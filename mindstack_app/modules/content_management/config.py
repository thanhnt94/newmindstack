class ContentManagementModuleDefaultConfig:
    ALLOWED_RICH_TEXT_EXTENSIONS = {
        '.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg', '.bmp',
        '.mp3', '.wav', '.ogg', '.m4a', '.aac', '.flac',
        '.mp4', '.webm', '.mov', '.mkv', '.avi',
        '.pdf', '.docx', '.pptx', '.xlsx', '.zip', '.rar', '.txt'
    }
    TYPE_SLUG_MAP = {
        'COURSE': 'courses',
        'FLASHCARD_SET': 'flashcards',
        'QUIZ_SET': 'quizzes'
    }
