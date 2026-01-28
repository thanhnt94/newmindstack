"""
Prompt Manager - Manages AI prompts and context injection.

Contains pure functions to build prompts from data.
No database or external API calls.
"""
import re
from typing import Dict, Any, Optional

# --- PROMPT TEMPLATES ---

DEFAULT_FLASHCARD_EXPLANATION_PROMPT = (
    "Với vai trò là một trợ lý học tập, hãy giải thích ngắn gọn, rõ ràng và dễ hiểu về thuật ngữ sau. "
    "Tập trung vào ý nghĩa cốt lõi, cung cấp ví dụ thực tế về cách dùng.\n\n"
    "**Thuật ngữ:** \"{front}\"\n"
    "**Định nghĩa/Ngữ cảnh:** \"{back}\"\n\n"
    "Hãy trình bày câu trả lời theo định dạng Markdown."
)

DEFAULT_QUIZ_EXPLANATION_PROMPT = (
    "Với vai trò là một trợ lý học tập, hãy giải thích cặn kẽ câu hỏi trắc nghiệm sau.\n\n"
    "**Bối cảnh (nếu có):**\n{pre_question_text}\n\n"
    "**Câu hỏi:**\n{question}\n"
    "A. {option_a}\n"
    "B. {option_b}\n"
    "C. {option_c}\n"
    "D. {option_d}\n\n"
    "**Đáp án đúng:** {correct_answer}\n"
    "**Hướng dẫn có sẵn:** {explanation}\n\n"
    "**Yêu cầu:**\n"
    "1. Phân tích tại sao đáp án '{correct_answer}' là đúng.\n"
    "2. Giải thích ngắn gọn tại sao các đáp án còn lại là sai.\n"
    "3. Cung cấp một mẹo hoặc kiến thức mở rộng hữu ích liên quan đến câu hỏi.\n"
    "Hãy trình bày câu trả lời một cách logic, rõ ràng, sử dụng định dạng Markdown."
)


class PromptManager:
    """Consolidated manager for prompt building."""

    @staticmethod
    def strip_bbcode(text: str) -> str:
        """Remove BBCode tags from text."""
        if not text:
            return ""
        # Simple regex to remove [b], [/b], etc.
        return re.sub(r'\[/?[^\]]+\]', '', str(text))

    @staticmethod
    def get_item_context_data(item_data: dict, container_data: Optional[dict] = None) -> Dict[str, Any]:
        """
        Prepare context data dictionary from item and container info.
        
        Args:
           item_data: Dict containing 'content', 'custom_data', 'item_type' etc.
           container_data: Dict containing 'title', 'ai_settings' etc.
        """
        data = {}
        
        # 1. Process Item Content
        content = item_data.get('content', {}) or {}
        for key, value in content.items():
            if key == 'options' and isinstance(value, dict):
                for opt_key, opt_val in value.items():
                    data[f"option_{opt_key.lower()}"] = PromptManager.strip_bbcode(opt_val)
            elif isinstance(value, str):
                data[key] = PromptManager.strip_bbcode(value)
            else:
                data[key] = value or ""
                
        # 2. Process Custom Data
        custom_data = item_data.get('custom_data', {}) or {}
        for key, value in custom_data.items():
            clean_value = PromptManager.strip_bbcode(value) if isinstance(value, str) else (value or "")
            data[f"custom_{key.lower()}"] = clean_value
            if key.lower() not in data:
                data[key.lower()] = clean_value

        # 3. Process Container Data
        if container_data:
            data['set_title'] = container_data.get('title', "")
            data['set_description'] = container_data.get('description', "")
            
            ai_prompt_value = container_data.get('ai_prompt')
            if not ai_prompt_value:
                ai_settings = container_data.get('ai_settings', {}) or {}
                ai_prompt_value = ai_settings.get('custom_prompt', '')
            data['set_custom_prompt'] = ai_prompt_value or ""

        # 4. Defaults
        default_keys = [
            'front', 'back', 'question', 'pre_question_text', 
            'option_a', 'option_b', 'option_c', 'option_d', 
            'correct_answer', 'explanation'
        ]
        for key in default_keys:
            data.setdefault(key, "")

        return data

    @staticmethod
    def build_explanation_prompt(
        item_data: dict, 
        container_data: Optional[dict] = None, 
        custom_question: Optional[str] = None
    ) -> Optional[str]:
        """
        Build the final prompt string for explaining an item.
        
        Logic:
        1. Check item-level custom prompt
        2. Check container-level custom prompt
        3. Use default template based on item_type
        4. Inject context data
        """
        raw_prompt = ""
        content = item_data.get('content', {}) or {}
        
        # 1. Item Level
        if content.get('ai_prompt'):
            raw_prompt = content.get('ai_prompt')
            
        # 2. Container Level
        if not raw_prompt and container_data:
            raw_prompt = container_data.get('ai_prompt') or \
                         (container_data.get('ai_settings', {}) or {}).get('custom_prompt')

        # 3. Defaults
        if not raw_prompt:
            item_type = item_data.get('item_type')
            if item_type == 'FLASHCARD':
                raw_prompt = DEFAULT_FLASHCARD_EXPLANATION_PROMPT
            elif item_type == 'QUIZ_MCQ':
                raw_prompt = DEFAULT_QUIZ_EXPLANATION_PROMPT

        # Custom Question Override
        if custom_question:
            context_info = ""
            item_type = item_data.get('item_type')
            if item_type == 'FLASHCARD':
                context_info = f"thuật ngữ \"{content.get('front', '')}\" với định nghĩa là \"{content.get('back', '')}\""
            elif item_type == 'QUIZ_MCQ':
                context_info = f"câu hỏi \"{content.get('question', '')}\""
            
            raw_prompt = (f"Dựa trên {context_info}, "
                          f"hãy trả lời câu hỏi sau một cách ngắn gọn và chính xác:\n\n"
                          f"**Câu hỏi:** \"{custom_question}\"")

        if not raw_prompt:
            return None

        # 4. Inject Context
        context_data = PromptManager.get_item_context_data(item_data, container_data)
        
        final_prompt = raw_prompt
        # Simple python format string replacement manually to be safe with partial keys
        for key, value in context_data.items():
            placeholder = "{" + key + "}"
            final_prompt = final_prompt.replace(placeholder, str(value))
            
        return final_prompt
