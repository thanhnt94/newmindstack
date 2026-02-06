from .services import generator_service

def generate_text(prompt, requester_module="external", session_id=None, delay_seconds=0, **kwargs):
    """
    Public API to request text generation.
    Returns the GenerationLog object (or its ID) immediately, processing happens async.
    """
    payload = {
        "prompt": prompt,
        "requester_module": requester_module,
        "session_id": session_id,
        "delay_seconds": int(delay_seconds),
        **kwargs
    }
    return generator_service.dispatch_text_generation(payload)

def generate_audio(text, voice_id, requester_module="external", session_id=None, delay_seconds=0, **kwargs):
    """
    Public API to request audio generation.
    """
    payload = {
        "text": text,
        "voice_id": voice_id,
        "requester_module": requester_module,
        "session_id": session_id,
        "delay_seconds": int(delay_seconds),
        **kwargs
    }
    return generator_service.dispatch_audio_generation(payload)

def generate_image(prompt, requester_module="external", session_id=None, delay_seconds=0, **kwargs):
    """
    Public API to request image generation.
    """
    payload = {
        "prompt": prompt,
        "requester_module": requester_module,
        "session_id": session_id,
        "delay_seconds": int(delay_seconds),
        **kwargs
    }
    return generator_service.dispatch_image_generation(payload)

def generate_bulk_from_container(container_id, options, requester_module="admin_bulk"):
    """
    Generate content for all items in a specific container.
    """
    return generator_service.dispatch_bulk_generation(container_id, options, requester_module)


def get_generation_status(log_id):
    """
    Check the status of a generation request.
    """
    return generator_service.get_log_status(log_id)

def get_log_model():
    """
    Get the GenerationLog model class.
    Used by Admin/Ops for direct queries or cleanup.
    """
    from .models import GenerationLog
    return GenerationLog
