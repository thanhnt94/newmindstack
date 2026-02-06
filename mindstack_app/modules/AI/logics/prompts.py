# File: mindstack_app/modules/ai_services/prompts.py
# Phiên bản: 2.2
# MỤC ĐÍCH: Triển khai logic phân cấp prompt.
# ĐÃ SỬA: Bổ sung logic để lấy prompt từ LearningItem, sau đó đến LearningContainer,
#         và cuối cùng là prompt mặc định.

# Prompt mặc định cho việc giải thích Flashcard
DEFAULT_FLASHCARD_EXPLANATION_PROMPT = (
    "Với vai trò là một trợ lý học tập, hãy giải thích ngắn gọn, rõ ràng và dễ hiểu về thuật ngữ sau. "
    "Tập trung vào ý nghĩa cốt lõi, cung cấp ví dụ thực tế về cách dùng.\n\n"
    "**Thuật ngữ:** \"{front}\"\n"
    "**Định nghĩa/Ngữ cảnh:** \"{back}\"\n\n"
    "Hãy trình bày câu trả lời theo định dạng Markdown."
)

# Prompt mặc định cho việc giải thích câu hỏi Quiz
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

DEFAULT_CUSTOM_QUESTION_PROMPT = (
    "Bạn là một trợ lý học tập thông minh. Người dùng đang xem xét một nội dung học tập và có câu hỏi riêng.\n"
    "Dưới đây là thông tin ngữ cảnh về nội dung đó:\n\n"
    "---\n"
    "{context_summary}\n"
    "---\n\n"
    "**Câu hỏi của người dùng:**\n"
    "\"{custom_question}\"\n\n"
    "Hãy trả lời câu hỏi trên một cách chính xác, ngắn gọn và hữu ích, bám sát vào ngữ cảnh đã cung cấp."
)

def _get_item_context_data(item):
    """
    Mô tả: Thu thập tất cả dữ liệu ngữ cảnh từ một LearningItem và LearningContainer liên quan
    để sử dụng trong việc format prompt.
    
    NEW: 
    - Strip BBCode từ tất cả text values để AI nhận text thuần
    - Hỗ trợ custom_data columns với placeholder {custom_xyz} và shorthand {xyz}
    
    Args:
        item (LearningItem): Đối tượng học liệu.

    Returns:
        dict: Một dictionary chứa tất cả dữ liệu có thể sử dụng làm placeholder.
    """
    from mindstack_app.utils.content_renderer import strip_bbcode
    
    data = {}
    
    # Lấy dữ liệu từ chính content của item (strip BBCode từ text)
    if isinstance(item.content, dict):
        for key, value in item.content.items():
            # Xử lý các options của quiz
            if key == 'options' and isinstance(value, dict):
                for opt_key, opt_val in value.items():
                    # Strip BBCode từ option values
                    data[f"option_{opt_key.lower()}"] = strip_bbcode(opt_val) if isinstance(opt_val, str) else (opt_val or "")
            elif isinstance(value, str):
                # Strip BBCode từ text fields (front, back, question, etc.)
                data[key] = strip_bbcode(value)
            else:
                data[key] = value or ""

    # [NEW] Lấy dữ liệu từ custom_data columns (nếu có)
    if item.custom_data and isinstance(item.custom_data, dict):
        for key, value in item.custom_data.items():
            # Strip BBCode nếu là string
            clean_value = strip_bbcode(value) if isinstance(value, str) else (value or "")
            # Cho phép dùng cả {custom_xyz} và {xyz} trong prompt
            data[f"custom_{key.lower()}"] = clean_value
            # Chỉ set shorthand nếu chưa có key trùng (không override built-in fields)
            if key.lower() not in data:
                data[key.lower()] = clean_value

    # Lấy dữ liệu từ các trường khác của item
    data['item_id'] = item.item_id
    data['item_type'] = item.item_type
    data['ai_explanation'] = item.ai_explanation or ""

    # Lấy dữ liệu từ LearningContainer (bộ chứa) thông qua backref
    # 'item.container' hoạt động được là nhờ 'backref="container"' trong model LearningContainer
    container = item.container
    if container:
        data['set_title'] = container.title or ""
        data['set_description'] = container.description or ""
        data['set_tags'] = container.tags or ""
        ai_prompt_value = getattr(container, 'ai_prompt', None)
        if not ai_prompt_value and hasattr(container, 'ai_settings'):
            settings_payload = container.ai_settings
            if isinstance(settings_payload, dict):
                ai_prompt_value = settings_payload.get('custom_prompt', '')
        data['set_custom_prompt'] = ai_prompt_value or ""

    # Cung cấp giá trị mặc định để tránh lỗi khi format
    # Các keys này tương ứng với các placeholder trong prompt mặc định
    default_keys = [
        'front', 'back', 'question', 'pre_question_text', 
        'option_a', 'option_b', 'option_c', 'option_d', 
        'correct_answer', 'explanation'
    ]
    for key in default_keys:
        data.setdefault(key, "")

    return data

def get_formatted_prompt(item, purpose='explanation', custom_question=None):
    """
    Mô tả: Lấy prompt phù hợp và điền dữ liệu ngữ cảnh vào đó.

    Args:
        item (LearningItem): Đối tượng học liệu.
        purpose (str): Mục đích của prompt ('explanation', 'custom_question').
        custom_question (str, optional): Câu hỏi tùy chỉnh từ người dùng.

    Returns:
        str: Một câu lệnh hoàn chỉnh đã được format để gửi cho AI.
    """
    raw_prompt = ""
    container = item.container
    
    # 1. Ưu tiên prompt tùy chỉnh trong content của item
    if isinstance(item.content, dict) and item.content.get('ai_prompt'):
        raw_prompt = item.content.get('ai_prompt')
    
    # 2. Nếu không có, dùng prompt tùy chỉnh của container
    if not raw_prompt and container:
        ai_prompt_value = getattr(container, 'ai_prompt', None)
        if ai_prompt_value:
            raw_prompt = ai_prompt_value
        elif hasattr(container, 'ai_settings') and isinstance(container.ai_settings, dict):
            raw_prompt = container.ai_settings.get('custom_prompt')

    # 3. Nếu vẫn không có, dùng prompt mặc định theo loại item
    if not raw_prompt:
        if item.item_type == 'FLASHCARD':
            raw_prompt = DEFAULT_FLASHCARD_EXPLANATION_PROMPT
        elif item.item_type == 'QUIZ_MCQ':
            raw_prompt = DEFAULT_QUIZ_EXPLANATION_PROMPT

    # Xử lý trường hợp câu hỏi tùy chỉnh
    if purpose == 'custom_question' and custom_question:
        # Xây dựng context summary dựa trên loại item
        context_summary = ""
        c = item.content or {}
        if item.item_type == 'FLASHCARD':
            context_summary = (
                f"Thuật ngữ: {c.get('front', '')}\n"
                f"Định nghĩa: {c.get('back', '')}"
            )
        elif item.item_type == 'QUIZ_MCQ':
            options_text = "\n".join([f"- {k}: {v}" for k, v in c.get('options', {}).items()])
            context_summary = (
                f"Câu hỏi: {c.get('question', '')}\n"
                f"Các lựa chọn:\n{options_text}\n"
                f"Đáp án đúng: {c.get('correct_answer', '')}\n"
                f"Giải thích gốc: {c.get('explanation', '')}"
            )
        else:
            context_summary = f"Nội dung: {c}"

        raw_prompt = DEFAULT_CUSTOM_QUESTION_PROMPT.format(
            context_summary=context_summary, 
            custom_question=custom_question
        )
        return raw_prompt

    if not raw_prompt:
        return None

    # Lấy dữ liệu ngữ cảnh
    context_data = _get_item_context_data(item)
    
    # Format prompt
    final_prompt = raw_prompt
    for key, value in context_data.items():
        placeholder = "{" + key + "}"
        final_prompt = final_prompt.replace(placeholder, str(value))
        
    return final_prompt
