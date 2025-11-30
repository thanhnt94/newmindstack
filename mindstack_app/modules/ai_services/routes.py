# File: mindstack_app/modules/ai_services/routes.py
# Phiên bản: 2.2
# MỤC ĐÍCH: Nâng cấp endpoint để sử dụng hệ thống prompt động mới và cơ chế cache.
# ĐÃ SỬA: Thêm logic kiểm tra cache (ai_explanation) và lưu kết quả từ AI.
# ĐÃ THÊM: Hỗ trợ tham số force_regenerate để bỏ qua cache và tạo lại nội dung.

from flask import request, jsonify, current_app
from flask_login import login_required
from . import ai_services_bp
from .gemini_client import get_gemini_client
from .prompts import get_formatted_prompt
from ...models import db, LearningItem
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
        return jsonify({'success': True, 'response': item.ai_explanation})

    # Lấy client Gemini
    gemini_client = get_gemini_client()
    if not gemini_client:
        return jsonify({'success': False, 'message': 'Dịch vụ AI chưa được cấu hình (thiếu API key).'}), 503

    # 2. Tạo prompt động
    final_prompt = get_formatted_prompt(item, purpose=prompt_type, custom_question=custom_question)
    
    if not final_prompt:
        return jsonify({'success': False, 'message': 'Không thể tạo prompt cho loại học liệu này.'}), 400
    
    # 3. Gọi Gemini API để lấy phản hồi
    try:
        item_info = f"{item.item_type} ID {item.item_id}"
        success, ai_response = gemini_client.generate_content(final_prompt, item_info)

        if not success:
            return jsonify({'success': False, 'message': ai_response}), 503

        # 4. Nếu là yêu cầu giải thích, lưu lại kết quả vào cache
        if prompt_type == 'explanation':
            item.ai_explanation = ai_response
            db.session.commit()
            current_app.logger.info(f"AI Service: Đã lưu cache cho item {item_id}.")

        return jsonify({'success': True, 'response': ai_response})
    except Exception as e:
        current_app.logger.error(f"Lỗi khi xử lý yêu cầu AI cho item {item_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi phía máy chủ khi xử lý yêu cầu AI.'}), 500