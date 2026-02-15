
import sys
from unittest.mock import MagicMock

# 1. Comprehensive Mocks
mock_flask = MagicMock()
mock_flask.current_app.config = {'UPLOAD_FOLDER': 'uploads'}
mock_flask.current_app.logger = MagicMock()
sys.modules['flask'] = mock_flask

# Mock flask_login
sys.modules['flask_login'] = MagicMock()

# Mock SQLAlchemy models
mock_models = MagicMock()
sys.modules['mindstack_app.models'] = mock_models

# Mock Audio Interface
mock_audio = MagicMock()
sys.modules['mindstack_app.modules.audio.interface'] = mock_audio

# Mock Media Paths
import os
def mock_build_relative_media_path(val, folder):
    if not val: return None
    if "/" in val: return val
    # If it's just a filename, prepend folder
    return f"{folder}/{val}".replace('\\', '/')

mock_media_paths = MagicMock()
mock_media_paths.build_relative_media_path.side_effect = mock_build_relative_media_path
mock_media_paths.normalize_media_folder.side_effect = lambda x: x
sys.modules['mindstack_app.utils.media_paths'] = mock_media_paths

# Mock session manager and algorithms
sys.modules['mindstack_app.modules.vocabulary.mcq.services.mcq_session_manager'] = MagicMock()
sys.modules['mindstack_app.modules.vocabulary.mcq.logics.algorithms'] = MagicMock()

# 2. Mock Asyncio
mock_asyncio = MagicMock()
sys.modules['asyncio'] = mock_asyncio

# 3. Import the service
from mindstack_app.modules.vocabulary.mcq.services.mcq_service import MCQService

def test_mcq_audio_resolution():
    print("Running test_mcq_audio_resolution...")
    
    # CASE 1: Existing relative URL (just filename)
    item_data_1 = {
        'item_id': 2696,
        'content': {
            'front': 'Test 1',
            'front_audio': 'front_2696.mp3'
        }
    }
    
    container = MagicMock()
    container.settings = {'media_folders': {'audio': 'mimi_n2/audio'}}
    container.media_audio_folder = 'legacy_audio'
    
    MCQService.ensure_audio_urls(item_data_1, container)
    
    url_1 = item_data_1['content'].get('front_audio')
    print(f"Case 1 (filename only): {url_1}")
    assert url_1 == '/media/mimi_n2/audio/front_2696.mp3'

    # CASE 2: Existing path relative to uploads root
    item_data_2 = {
        'item_id': 2697,
        'content': {
            'front': 'Test 2',
            'front_audio': 'custom_set/audio/voice.mp3'
        }
    }
    
    MCQService.ensure_audio_urls(item_data_2, container)
    url_2 = item_data_2['content'].get('front_audio')
    print(f"Case 2 (relative path): {url_2}")
    assert url_2 == '/media/custom_set/audio/voice.mp3'

    # CASE 3: Already absolute
    item_data_3 = {
        'item_id': 2698,
        'content': {
            'front': 'Test 3',
            'front_audio': '/media/direct/path.mp3'
        }
    }
    MCQService.ensure_audio_urls(item_data_3, container)
    url_3 = item_data_3['content'].get('front_audio')
    print(f"Case 3 (already absolute): {url_3}")
    assert url_3 == '/media/direct/path.mp3'

    print("SUCCESS: MCQ audio URL resolution verified!")

if __name__ == "__main__":
    try:
        test_mcq_audio_resolution()
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
