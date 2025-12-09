# File: mindstack_app/modules/ai_services/routes.py
# Phiên bản: 2.2
# MỤC ĐÍCH: Nâng cấp endpoint để sử dụng hệ thống prompt động mới và cơ chế cache.
# ĐÃ SỬA: Thêm logic kiểm tra cache (ai_explanation) và lưu kết quả từ AI.
# ĐÃ THÊM: Hỗ trợ tham số force_regenerate để bỏ qua cache và tạo lại nội dung.

from flask import request, jsonify, current_app
from flask_login import login_required
import mistune
from . import ai_services_bp
from .service_manager import get_ai_service
from .prompts import get_formatted_prompt
from ...models import db, LearningItem
from ...modules.shared.utils.html_sanitizer import sanitize_rich_text
from sqlalchemy.orm.attributes import flag_modified

@ai_services_bp.route('/ai/get-ai-response', methods=['POST'])
@login_required
def get_ai_response():
    """
    Mô tả: Endpoint chính để nhận yêu cầu từ frontend và trả về phản hồi từ AI.
    Sử dụng hệ thống prompt động để tạo câu lệnh cho AI và cơ chế cache.
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Yêu cầu không hợp lệ.'}), 400

    prompt_type = data.get('prompt_type', 'explanation') # Mặc định là 'explanation'
    item_id = data.get('item_id')
    custom_question = data.get('custom_question')
    force_regenerate = data.get('force_regenerate', False)

    if not item_id:
        return jsonify({'success': False, 'message': 'Thiếu thông tin item_id.'}), 400

    item = LearningItem.query.get(item_id)
    if not item:
        return jsonify({'success': False, 'message': 'Không tìm thấy học liệu.'}), 404

    # 1. Kiểm tra cache trước khi gọi AI, trừ khi có yêu cầu tái tạo
    if prompt_type == 'explanation' and item.ai_explanation and not force_regenerate:
        current_app.logger.info(f"AI Service: Trả về cache cho item {item_id}.")
        # Đảm bảo cache trả về cũng là HTML
        html_content = sanitize_rich_text(mistune.html(item.ai_explanation))
        return jsonify({'success': True, 'response': html_content})

    # Lấy client AI (Gemini hoặc HF tùy cấu hình)
    ai_client = get_ai_service()
    if not ai_client:
        return jsonify({'success': False, 'message': 'Dịch vụ AI chưa được cấu hình (thiếu API key).'}), 503

    # 2. Tạo prompt động
    final_prompt = get_formatted_prompt(item, purpose=prompt_type, custom_question=custom_question)
    
    if not final_prompt:
        return jsonify({'success': False, 'message': 'Không thể tạo prompt cho loại học liệu này.'}), 400
    
    # 3. Gọi AI API để lấy phản hồi
    try:
        item_info = f"{item.item_type} ID {item.item_id}"
        success, ai_response = ai_client.generate_content(final_prompt, item_info)

        if not success:
            return jsonify({'success': False, 'message': ai_response}), 503

        # 4. Nếu là yêu cầu giải thích, chuyển Markdown sang HTML, sanitize và lưu lại kết quả
        if prompt_type == 'explanation':
            # Giữ lại bản gốc Markdown để có thể tái tạo nếu cần
            # item.ai_explanation_raw = ai_response 
            
            html_content = sanitize_rich_text(mistune.html(ai_response))
            item.ai_explanation = html_content
            db.session.commit()
            current_app.logger.info(f"AI Service: Đã lưu cache (HTML) cho item {item_id}.")
            return jsonify({'success': True, 'response': html_content})

        # Đối với các loại khác, trả về response gốc
        return jsonify({'success': True, 'response': ai_response})
    except Exception as e:
        current_app.logger.error(f"Lỗi khi xử lý yêu cầu AI cho item {item_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi phía máy chủ khi xử lý yêu cầu AI.'}), 500