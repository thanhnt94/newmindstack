# File: mindstack_app/modules/ai_services/prompts.py
# Phiên bản: 2.1
# MỤC ĐÍCH: Thêm chú thích để làm rõ logic truy cập container.
# ĐÃ SỬA: Bổ sung comment giải thích về backref.

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

def _get_item_context_data(item):
    """
    Mô tả: Thu thập tất cả dữ liệu ngữ cảnh từ một LearningItem và LearningContainer liên quan
    để sử dụng trong việc format prompt.
    
    Args:
        item (LearningItem): Đối tượng học liệu.

    Returns:
        dict: Một dictionary chứa tất cả dữ liệu có thể sử dụng làm placeholder.
    """
    data = {}
    
    # Lấy dữ liệu từ chính content của item
    if isinstance(item.content, dict):
        for key, value in item.content.items():
            # Xử lý các options của quiz
            if key == 'options' and isinstance(value, dict):
                for opt_key, opt_val in value.items():
                    data[f"option_{opt_key.lower()}"] = opt_val or ""
            else:
                data[key] = value or ""

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
        if isinstance(container.ai_settings, dict):
            data['set_custom_prompt'] = container.ai_settings.get('custom_prompt', '')

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
    
    # 1. Ưu tiên prompt tùy chỉnh trong 'ai_settings' của container
    if container and isinstance(container.ai_settings, dict):
        raw_prompt = container.ai_settings.get('custom_prompt')

    # 2. Nếu không có, dùng prompt mặc định theo loại item
    if not raw_prompt:
        if item.item_type == 'FLASHCARD':
            raw_prompt = DEFAULT_FLASHCARD_EXPLANATION_PROMPT
        elif item.item_type == 'QUIZ_MCQ':
            raw_prompt = DEFAULT_QUIZ_EXPLANATION_PROMPT

    # Xử lý trường hợp câu hỏi tùy chỉnh
    if purpose == 'custom_question' and custom_question:
        context_info = ""
        if item.item_type == 'FLASHCARD':
            context_info = f"thuật ngữ \"{item.content.get('front', '')}\" với định nghĩa là \"{item.content.get('back', '')}\""
        elif item.item_type == 'QUIZ_MCQ':
            context_info = f"câu hỏi \"{item.content.get('question', '')}\""
            
        raw_prompt = (f"Dựa trên {context_info}, "
                      f"hãy trả lời câu hỏi sau một cách ngắn gọn và chính xác:\n\n"
                      f"**Câu hỏi:** \"{custom_question}\"")

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