from marshmallow import Schema, fields, validate

# --- Base Schemas ---

class GenerationRequestBase(Schema):
    """Base schema for all generation requests."""
    requester_module = fields.Str(required=False, load_default="unknown")
    session_id = fields.Str(required=False, load_default=None)
    delay_seconds = fields.Int(load_default=0, validate=validate.Range(min=0, max=3600))

# --- Specific Schemas ---

class TextGenerationSchema(GenerationRequestBase):
    prompt = fields.Str(required=True, validate=validate.Length(min=1))
    system_instruction = fields.Str(required=False, load_default="")
    model = fields.Str(load_default="gpt-4o")
    temperature = fields.Float(load_default=0.7)
    max_tokens = fields.Int(load_default=1000)

class AudioGenerationSchema(GenerationRequestBase):
    text = fields.Str(required=True, validate=validate.Length(min=1))
    voice_id = fields.Str(required=True)
    model = fields.Str(load_default="eleven_multilingual_v2")
    stability = fields.Float(load_default=0.5)

class ImageGenerationSchema(GenerationRequestBase):
    prompt = fields.Str(required=True, validate=validate.Length(min=1))
    size = fields.Str(load_default="1024x1024", validate=validate.OneOf(["256x256", "512x512", "1024x1024"]))
    quality = fields.Str(load_default="standard")
    n = fields.Int(load_default=1)

# --- Output Schemas ---

class GenerationResponseSchema(Schema):
    task_id = fields.Str()
    status = fields.Str()
    result = fields.Dict(allow_none=True)
    error = fields.Str(allow_none=True)
