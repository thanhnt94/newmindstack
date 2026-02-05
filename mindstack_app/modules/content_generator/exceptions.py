class ContentGeneratorError(Exception):
    """Base exception for content generator module."""
    pass

class AIProviderError(ContentGeneratorError):
    """Raised when external AI API fails or returns error."""
    pass

class InvalidRequestError(ContentGeneratorError):
    """Raised when input data is invalid."""
    pass

class ConfigurationError(ContentGeneratorError):
    """Raised when API keys or settings are missing."""
    pass
