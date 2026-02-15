
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
mock_media_paths = MagicMock()
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

def test_mcq_audio_naming():
    print("Running test_mcq_audio_naming (Refined)...")
    
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
    mock_audio_response = MagicMock()
    mock_audio_response.status = 'generated'
    mock_audio_response.url = '/media/vocab_audio/front_1234.mp3'
    
    # Mock the return value of run_until_complete
    mock_asyncio.new_event_loop.return_value.run_until_complete.return_value = mock_audio_response
    
    # Execute
    MCQService.ensure_audio_urls(item_data, container)
    
    # Verify
    content = item_data['content']
    print(f"Resulting content: {content}")
    
    assert content.get('front_audio') == '/media/vocab_audio/front_1234.mp3'
    assert content.get('front_audio_url') == '/media/vocab_audio/front_1234.mp3'
    
    # Verify AudioInterface call args
    mock_audio.AudioInterface.generate_audio.assert_called()
    _, kwargs = mock_audio.AudioInterface.generate_audio.call_args
    print(f"generate_audio called with target_dir={kwargs['target_dir']} and filename={kwargs['custom_filename']}")
    
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
