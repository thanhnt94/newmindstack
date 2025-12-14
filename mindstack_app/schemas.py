from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, List, Any

class FlashcardContent(BaseModel):
    front: str
    back: str
    front_img: Optional[str] = None
    back_img: Optional[str] = None
    front_audio_url: Optional[str] = None
    back_audio_url: Optional[str] = None
    front_audio_content: Optional[str] = None
    back_audio_content: Optional[str] = None
    ai_explanation: Optional[str] = None
    ai_prompt: Optional[str] = None
    # Capabilities flags
    supports_pronunciation: Optional[bool] = False
    supports_writing: Optional[bool] = False
    supports_quiz: Optional[bool] = False
    supports_essay: Optional[bool] = False
    supports_listening: Optional[bool] = False
    supports_speaking: Optional[bool] = False
    
    class Config:
        extra = "ignore" # Bỏ qua các trường thừa nếu có

class QuizContent(BaseModel):
    question: str
    options: Dict[str, str] # {"A": "...", "B": "..."}
    correct_answer: str
    explanation: Optional[str] = None
    pre_question_text: Optional[str] = None
    question_image_file: Optional[str] = None
    question_audio_file: Optional[str] = None
    ai_prompt: Optional[str] = None
    
    class Config:
        extra = "ignore"
