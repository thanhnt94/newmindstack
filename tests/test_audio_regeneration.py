import io
import os
import shutil
import zipfile

import pandas as pd

from mindstack_app import db
from mindstack_app.models import LearningContainer, LearningItem, User


def _login(client, user_id):
    with client.session_transaction() as session:
        session['_user_id'] = str(user_id)
        session['_fresh'] = True


def test_regenerate_audio_moves_files_and_updates_export(app, monkeypatch, tmp_path):
    with app.app_context():
        admin = User(username='tester', email='tester@example.com', user_role=User.ROLE_ADMIN)
        admin.set_password('password')
        db.session.add(admin)
        db.session.flush()

        container = LearningContainer(
            creator_user_id=admin.user_id,
            container_type='FLASHCARD_SET',
            title='Audio Moves',
            is_public=False,
        )
        db.session.add(container)
        db.session.flush()

        legacy_filename = 'legacy_sample.mp3'
        item = LearningItem(
            container_id=container.container_id,
            item_type='FLASHCARD',
            order_in_container=1,
            content={
                'front': 'Front text',
                'back': 'Back text',
                'front_audio_url': f'flashcard/audio/cache/{legacy_filename}',
            },
        )
        db.session.add(item)
        db.session.commit()

        item_id = item.item_id
        user_id = admin.user_id
        container_id = container.container_id

    uploads_root = app.static_folder
    cache_dir = os.path.join(uploads_root, 'flashcard', 'audio', 'cache')
    os.makedirs(cache_dir, exist_ok=True)

    legacy_source = tmp_path / legacy_filename
    legacy_source.write_bytes(b'legacy-audio')
    shutil.copy2(legacy_source, os.path.join(cache_dir, legacy_filename))

    generated_source = tmp_path / 'generated.mp3'
    generated_source.write_bytes(b'generated-audio')

    async def _fake_get_cached_or_generate_audio(_content):
        return str(generated_source), True, 'ok'

    monkeypatch.setattr(
        'mindstack_app.modules.learning.flashcard_learning.routes.audio_service.get_cached_or_generate_audio',
        _fake_get_cached_or_generate_audio,
    )

    client = app.test_client()
    _login(client, user_id)

    response = client.post(
        '/learn/regenerate-audio-from-content',
        json={
            'item_id': item_id,
            'side': 'back',
            'content_to_read': 'example text',
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['relative_path'].startswith('media/audio/')

    with app.app_context():
        updated_item = LearningItem.query.get(item_id)
        assert updated_item.content['back_audio_url'] == payload['relative_path']
        assert updated_item.content['front_audio_url'].startswith('media/audio/')

        front_file = os.path.join(app.static_folder, updated_item.content['front_audio_url'])
        back_file = os.path.join(app.static_folder, updated_item.content['back_audio_url'])
        assert os.path.isfile(front_file)
        assert os.path.isfile(back_file)

    export_response = client.get(f'/content/flashcards/{container_id}/export')
    assert export_response.status_code == 200

    zip_buffer = io.BytesIO(export_response.data)
    with zipfile.ZipFile(zip_buffer) as archive:
        excel_bytes = archive.read('flashcards.xlsx')
        exported_audio_files = [
            name for name in archive.namelist() if name.startswith('media/audio/')
        ]
        assert exported_audio_files, 'Exported package should include audio files in media/audio/'

    data_frame = pd.read_excel(io.BytesIO(excel_bytes), sheet_name='Data')
    row = data_frame.loc[data_frame['item_id'] == item_id].iloc[0]
    assert row['front_audio_url'].startswith('media/audio/')
    assert row['back_audio_url'].startswith('media/audio/')
