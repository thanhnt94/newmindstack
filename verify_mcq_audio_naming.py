
import os
import sys
from unittest.mock import MagicMock

# Mock Flask current_app and context
sys.modules['flask'] = MagicMock()
import flask
flask.current_app = MagicMock()
flask.current_app.config = {'UPLOAD_FOLDER': 'uploads'}

# Mock asyncio loop
import asyncio
sys.modules['asyncio'] = MagicMock()

# Mock AudioInterface
sys.modules['mindstack_app.modules.audio.interface'] = MagicMock()
from mindstack_app.modules.audio.interface import AudioInterface

# Mock media_paths
sys.modules['mindstack_app.utils.media_paths'] = MagicMock()
from mindstack_app.utils.media_paths import normalize_media_folder
normalize_media_folder.side_effect = lambda x: x

# Now import MCQService
# We need to bypass the actual DB models import if possible, or mock them
sys.modules['mindstack_app.models'] = MagicMock()
from mindstack_app.modules.vocabulary.mcq.services.mcq_service import MCQService

def test_mcq_audio_naming():
    print("Running test_mcq_audio_naming...")
    
    # Setup mock data
    item_data = {
        'item_id': 1234,
        'content': {
            'front': 'Test Question',
            'back': 'Test Answer'
        }
    }
    
    container = MagicMock()
    container.settings = {'media_folders': {'audio': 'vocab_audio'}}
    container.media_audio_folder = 'legacy_audio'
    
    # Mock AudioInterface response
    mock_response = MagicMock()
    mock_response.status = 'generated'
    mock_response.url = '/media/vocab_audio/front_1234.mp3'
    
    # We need to mock the loop.run_until_complete return value
    # Since we mocked asyncio, we'll mock the behavior inside ensure_audio_urls
    
    # Let's mock the AudioInterface.generate_audio call
    AudioInterface.generate_audio.return_value = MagicMock() # This is the coroutine
    
    # Because ensure_audio_urls uses asyncio.new_event_loop().run_until_complete()
    # and we mocked asyncio, we need to ensure it returns our mock_response
    import asyncio
    asyncio.new_event_loop().run_until_complete.return_value = mock_response
    
    # Execute
    MCQService.ensure_audio_urls(item_data, container)
    
    # Verify
    content = item_data['content']
    print(f"Resulting content hooks: {content}")
    
    assert content.get('front_audio') == '/media/vocab_audio/front_1234.mp3'
    assert content.get('front_audio_url') == '/media/vocab_audio/front_1234.mp3'
    
    # Verify AudioInterface call args
    AudioInterface.generate_audio.assert_called()
    args, kwargs = AudioInterface.generate_audio.call_args
    print(f"generate_audio called with: {kwargs}")
    
    assert kwargs['custom_filename'] == 'front_1234.mp3'
    assert kwargs['target_dir'] == 'uploads/vocab_audio'
    
    print("SUCCESS: MCQ audio naming convention verified!")

if __name__ == "__main__":
    try:
        test_mcq_audio_naming()
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
