# File: mindstack_app/modules/audio/config.py

class AudioModuleDefaultConfig:
    AUDIO_DEFAULT_ENGINE = "edge"
    AUDIO_DEFAULT_VOICE_EDGE = "vi-VN-HoaiMyNeural"
    AUDIO_DEFAULT_VOICE_GTTS = "vi"
    AUDIO_VOICE_MAPPING_GLOBAL = {
        'vi': 'edge:vi-VN-HoaiMyNeural',
        'en': 'gtts:en',
        'ja': 'edge:ja-JP-NanamiNeural',
        'vi-f': 'edge:vi-VN-HoaiMyNeural',
        'vi-m': 'edge:vi-VN-NamMinhNeural',
        'en-f': 'edge:en-US-AriaNeural',
        'en-m': 'edge:en-US-ChristopherNeural',
        'ja-f': 'edge:ja-JP-NanamiNeural',
        'ja-m': 'edge:ja-JP-KeitaNeural',
    }
