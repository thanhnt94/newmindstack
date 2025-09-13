# File: mindstack_app/modules/ai_services/routes.py
# Phiên bản: 2.0
# MỤC ĐÍCH: Nâng cấp endpoint để sử dụng hệ thống prompt động mới.
# ĐÃ SỬA: Thay thế các hàm get_prompt cũ bằng get_formatted_prompt.
# ĐÃ SỬA: Đơn giản hóa logic lấy ngữ cảnh.

from flask import request, jsonify, current_app
from flask_login import login_required
from . import ai_services_bp
from .gemini_client import get_gemini_client
from .prompts import get_formatted_prompt
from ...models import LearningItem

@ai_services_bp.route('/ai/get-ai-response', methods=['POST'])
@login_required
def get_ai_response():
    """
    Mô tả: Endpoint chính để nhận yêu cầu từ frontend và trả về phản hồi từ AI.
    Sử dụng hệ thống prompt động để tạo câu lệnh cho AI.
    """
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'Yêu cầu không hợp lệ.'}), 400

    prompt_type = data.get('prompt_type', 'explanation') # Mặc định là 'explanation'
    item_id = data.get('item_id')
    custom_question = data.get('custom_question')

    if not item_id:
        return jsonify({'success': False, 'message': 'Thiếu thông tin item_id.'}), 400

    # Lấy client Gemini
    gemini_client = get_gemini_client()
    if not gemini_client:
        return jsonify({'success': False, 'message': 'Dịch vụ AI chưa được cấu hình (thiếu API key).'}), 503

    # Lấy học liệu từ DB
    item = LearningItem.query.get(item_id)
    if not item:
        return jsonify({'success': False, 'message': 'Không tìm thấy học liệu.'}), 404

    # Tạo prompt động dựa trên item và loại yêu cầu
    final_prompt = get_formatted_prompt(item, purpose=prompt_type, custom_question=custom_question)
    
    if not final_prompt:
        return jsonify({'success': False, 'message': 'Không thể tạo prompt cho loại học liệu này.'}), 400
    
    # Gọi Gemini API để lấy phản hồi
    try:
        item_info = f"{item.item_type} ID {item.item_id}"
        ai_response = gemini_client.generate_content(final_prompt, item_info)
        
        # Kiểm tra nếu AI trả về thông báo lỗi
        if "Lỗi:" in ai_response or "AI không thể" in ai_response:
             return jsonify({'success': False, 'message': ai_response})

        return jsonify({'success': True, 'response': ai_response})
    except Exception as e:
        current_app.logger.error(f"Lỗi khi xử lý yêu cầu AI cho item {item_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi phía máy chủ khi xử lý yêu cầu AI.'}), 500