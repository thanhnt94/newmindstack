class DefaultConfig:
    """
    Default configuration for the Content Generator module.
    These values can be overridden in the main application config.
    """
    CONTENT_GENERATOR_ENABLED = True
    
    # AI Providers (Should be loaded from env vars or system settings in production)
    CONTENT_GEN_OPENAI_API_KEY = None
    CONTENT_GEN_ELEVENLABS_API_KEY = None
    CONTENT_GEN_STABLE_DIFFUSION_KEY = None
    
    # Default Limits
    CONTENT_GEN_MAX_TOKENS = 2000
    CONTENT_GEN_TIMEOUT = 60
