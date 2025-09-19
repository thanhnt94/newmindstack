# File: mindstack_app/modules/notes/routes.py
# Phiên bản: 1.0
# Mục đích: Chứa các route và logic cho tính năng ghi chú của người dùng.

from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from . import notes_bp
from .forms import NoteForm
from ...models import db, UserNote, LearningItem

@notes_bp.route('/notes/get/<int:item_id>', methods=['GET'])
@login_required
def get_note(item_id):
    """
    Mô tả: API endpoint để lấy nội dung ghi chú cho một học liệu cụ thể.
    """
    note = UserNote.query.filter_by(user_id=current_user.user_id, item_id=item_id).first()
    if note:
        return jsonify({'success': True, 'content': note.content})
    else:
        return jsonify({'success': False, 'content': ''})

@notes_bp.route('/notes/save/<int:item_id>', methods=['POST'])
@login_required
def save_note(item_id):
    """
    Mô tả: API endpoint để lưu hoặc cập nhật ghi chú cho một học liệu.
    """
    data = request.get_json()
    content = data.get('content')

    if content is None:
        return jsonify({'success': False, 'message': 'Nội dung không hợp lệ.'}), 400

    # Kiểm tra xem học liệu có tồn tại không
    item = LearningItem.query.get(item_id)
    if not item:
        return jsonify({'success': False, 'message': 'Học liệu không tồn tại.'}), 404

    note = UserNote.query.filter_by(user_id=current_user.user_id, item_id=item_id).first()

    if note:
        # Cập nhật ghi chú đã có
        note.content = content
    else:
        # Tạo ghi chú mới
        note = UserNote(user_id=current_user.user_id, item_id=item_id, content=content)
        db.session.add(note)
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Đã lưu ghi chú.'})

@notes_bp.route('/notes')
@login_required
def manage_notes():
    """
    Mô tả: Hiển thị trang quản lý tất cả các ghi chú của người dùng.
    """
    # Lấy tất cả ghi chú của người dùng và thông tin thẻ liên quan
    notes = db.session.query(UserNote, LearningItem).join(
        LearningItem, UserNote.item_id == LearningItem.item_id
    ).filter(
        UserNote.user_id == current_user.user_id
    ).order_by(UserNote.created_at.desc()).all()

    return render_template('notes/manage_notes.html', notes_with_items=notes)