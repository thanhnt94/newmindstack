# File: mindstack_app/modules/learning/flashcard_learning/routes.py
# Phiên bản: 1.1
# Mục đích: Định nghĩa các routes và logic cho module học Flashcard.
# ĐÃ SỬA: Loại bỏ toàn bộ logic batch_size và cập nhật các route để phù hợp với mô hình 1 thẻ/lần.

from flask import Blueprint, render_template, request, jsonify, abort, current_app, redirect, url_for, flash, session
from flask_login import login_required, current_user
import traceback
from .algorithms import get_new_only_items, get_due_items, get_hard_items, get_filtered_flashcard_sets, get_flashcard_mode_counts
from .session_manager import FlashcardSessionManager
from .config import FlashcardLearningConfig
from ....models import db, User, UserContainerState, LearningContainer
from sqlalchemy.sql import func


flashcard_learning_bp = Blueprint('flashcard_learning', __name__,
                                  template_folder='templates')


@flashcard_learning_bp.route('/flashcard_learning_dashboard')
@login_required
def flashcard_learning_dashboard():
    """
    Hiển thị trang chính để chọn bộ thẻ và chế độ học Flashcard.
    """
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)
    current_filter = request.args.get('filter', 'doing', type=str)

    flashcard_set_search_options = {
        'title': 'Tiêu đề', 'description': 'Mô tả', 'tags': 'Thẻ'
    }

    template_vars = {
        'search_query': search_query,
        'search_field': search_field,
        'flashcard_set_search_options': flashcard_set_search_options,
        'current_filter': current_filter
    }
    return render_template('flashcard_learning_dashboard.html', **template_vars)


@flashcard_learning_bp.route('/get_flashcard_modes_partial/all', methods=['GET'])
@login_required
def get_flashcard_modes_partial_all():
    """
    Trả về partial HTML chứa các chế độ học và số lượng thẻ tương ứng cho TẤT CẢ các bộ Flashcard.
    """
    selected_mode = request.args.get('selected_mode', None, type=str)

    modes = get_flashcard_mode_counts(current_user.user_id, 'all')
    return render_template('_flashcard_modes_selection.html',
                           modes=modes,
                           selected_set_id='all',
                           selected_flashcard_mode_id=selected_mode
                           )


@flashcard_learning_bp.route('/get_flashcard_modes_partial/multi/<string:set_ids_str>', methods=['GET'])
@login_required
def get_flashcard_modes_partial_multi(set_ids_str):
    """
    Trả về partial HTML chứa các chế độ học và số lượng thẻ tương ứng cho NHIỀU bộ Flashcard.
    """
    selected_mode = request.args.get('selected_mode', None, type=str)

    try:
        set_ids = [int(s) for s in set_ids_str.split(',') if s]
        modes = get_flashcard_mode_counts(current_user.user_id, set_ids)
    except ValueError:
        return '<p class="text-red-500 text-center">Lỗi: Định dạng ID bộ thẻ không hợp lệ.</p>', 400

    return render_template('_flashcard_modes_selection.html',
                           modes=modes,
                           selected_set_id='multi',
                           selected_flashcard_mode_id=selected_mode
                           )


@flashcard_learning_bp.route('/get_flashcard_modes_partial/<int:set_id>', methods=['GET'])
@login_required
def get_flashcard_modes_partial_by_id(set_id):
    """
    Trả về partial HTML chứa các chế độ học và số lượng thẻ tương ứng cho một bộ Flashcard cụ thể.
    """
    selected_mode = request.args.get('selected_mode', None, type=str)

    modes = get_flashcard_mode_counts(current_user.user_id, set_id)

    return render_template('_flashcard_modes_selection.html',
                           modes=modes,
                           selected_set_id=str(set_id),
                           selected_flashcard_mode_id=selected_mode
                           )


@flashcard_learning_bp.route('/start_flashcard_session/all/<string:mode>', methods=['GET'])
@login_required
def start_flashcard_session_all(mode):
    """
    Bắt đầu một phiên học Flashcard cho TẤT CẢ các bộ thẻ.
    """
    set_ids = 'all'

    if FlashcardSessionManager.start_new_flashcard_session(set_ids, mode):
        return redirect(url_for('learning.flashcard_learning.flashcard_session'))
    else:
        flash('Không có thẻ nào để bắt đầu phiên học với các lựa chọn này.', 'warning')
        return redirect(url_for('learning.flashcard_learning.flashcard_learning_dashboard'))


@flashcard_learning_bp.route('/start_flashcard_session/multi/<string:mode>', methods=['GET'])
@login_required
def start_flashcard_session_multi(mode):
    """
    Bắt đầu một phiên học Flashcard cho nhiều bộ thẻ.
    """
    set_ids_str = request.args.get('set_ids')

    if not set_ids_str:
        flash('Lỗi: Thiếu thông tin bộ thẻ.', 'danger')
        return redirect(url_for('learning.flashcard_learning.flashcard_learning_dashboard'))

    try:
        set_ids = [int(s) for s in set_ids_str.split(',') if s]
    except ValueError:
        flash('Lỗi: Định dạng ID bộ thẻ không hợp lệ.', 'danger')
        return redirect(url_for('learning.flashcard_learning.flashcard_learning_dashboard'))

    if FlashcardSessionManager.start_new_flashcard_session(set_ids, mode):
        return redirect(url_for('learning.flashcard_learning.flashcard_session'))
    else:
        flash('Không có thẻ nào để bắt đầu phiên học với các lựa chọn này.', 'warning')
        return redirect(url_for('learning.flashcard_learning.flashcard_learning_dashboard'))


@flashcard_learning_bp.route('/start_flashcard_session/<int:set_id>/<string:mode>', methods=['GET'])
@login_required
def start_flashcard_session_by_id(set_id, mode):
    """
    Bắt đầu một phiên học Flashcard cho một bộ thẻ cụ thể.
    """
    if FlashcardSessionManager.start_new_flashcard_session(set_id, mode):
        return redirect(url_for('learning.flashcard_learning.flashcard_session'))
    else:
        flash('Không có thẻ nào để bắt đầu phiên học với các lựa chọn này.', 'warning')
        return redirect(url_for('learning.flashcard_learning.flashcard_learning_dashboard'))


@flashcard_learning_bp.route('/flashcard_session')
@login_required
def flashcard_session():
    """
    Hiển thị giao diện học Flashcard.
    """
    if 'flashcard_session' not in session:
        flash('Không có phiên học Flashcard nào đang hoạt động. Vui lòng chọn bộ thẻ để bắt đầu.', 'info')
        return redirect(url_for('learning.flashcard_learning.flashcard_learning_dashboard'))
    return render_template('flashcard_session.html')


@flashcard_learning_bp.route('/get_flashcard_batch', methods=['GET'])
@login_required
def get_flashcard_batch():
    """
    Trả về dữ liệu nhóm thẻ tiếp theo trong phiên học hiện tại.
    """
    current_app.logger.debug("--- Bắt đầu get_flashcard_batch ---")
    if 'flashcard_session' not in session:
        current_app.logger.warning("Phiên học không hợp lệ hoặc đã kết thúc khi gọi get_flashcard_batch.")
        return jsonify({'message': 'Phiên học không hợp lệ hoặc đã kết thúc.'}), 404

    session_manager = FlashcardSessionManager.from_dict(session['flashcard_session'])
    
    try:
        # Lấy một thẻ duy nhất mỗi lần
        flashcard_batch = session_manager.get_next_batch()
        session['flashcard_session'] = session_manager.to_dict()
        
        if flashcard_batch is None:
            session_manager.end_flashcard_session()
            current_app.logger.info(f"Phiên học Flashcard cho người dùng {current_user.user_id} đã kết thúc do hết thẻ.")
            current_app.logger.debug("--- Kết thúc get_flashcard_batch (Hết thẻ) ---")
            return jsonify({'message': 'Bạn đã hoàn thành tất cả các thẻ trong phiên học này!'}), 404
        
        # Vì chỉ có một thẻ, chúng ta có thể trả về trực tiếp
        flashcard_batch['session_correct_answers'] = session_manager.correct_answers
        flashcard_batch['session_total_answered'] = session_manager.correct_answers + session_manager.incorrect_answers + session_manager.vague_answers

        current_app.logger.debug("--- Kết thúc get_flashcard_batch (Thành công) ---")
        return jsonify(flashcard_batch)

    except Exception as e:
        current_app.logger.error(f"LỖI NGHIÊM TRỌNG khi lấy nhóm thẻ: {e}", exc_info=True)
        current_app.logger.debug("--- Kết thúc get_flashcard_batch (LỖI) ---")
        return jsonify({'message': f'Lỗi khi tải thẻ: {str(e)}'}), 500


@flashcard_learning_bp.route('/submit_flashcard_answer', methods=['POST'])
@login_required
def submit_flashcard_answer():
    """
    Nhận câu trả lời của người dùng (dễ, khó, bình thường), xử lý và cập nhật tiến độ.
    """
    current_app.logger.debug("--- Bắt đầu submit_flashcard_answer ---")
    data = request.get_json()
    item_id = data.get('item_id')
    user_answer = data.get('user_answer')

    if not item_id or not user_answer:
        current_app.logger.warning("Dữ liệu đáp án không hợp lệ khi submit_flashcard_answer.")
        return jsonify({'error': 'Dữ liệu đáp án không hợp lệ.'}), 400

    if 'flashcard_session' not in session:
        current_app.logger.warning("Không tìm thấy phiên học trong session khi submit_flashcard_answer.")
        return jsonify({'message': 'Phiên học không hợp lệ hoặc đã kết thúc.'}), 400

    session_manager = FlashcardSessionManager.from_dict(session['flashcard_session'])
    if not session_manager:
        current_app.logger.warning("Không tìm thấy SessionManager khi submit_flashcard_answer.")
        return jsonify({'message': 'Phiên học không hợp lệ hoặc đã kết thúc.'}), 400

    set_ids = session_manager.set_id
    if not isinstance(set_ids, list):
        if set_ids == 'all':
            pass
        else:
            set_ids = [set_ids]

    if set_ids and set_ids != ['all']:
        for s_id in set_ids:
            try:
                user_container_state = UserContainerState.query.filter_by(
                    user_id=current_user.user_id,
                    container_id=s_id
                ).first()
                if not user_container_state:
                    user_container_state = UserContainerState(
                        user_id=current_user.user_id,
                        container_id=s_id,
                        is_archived=False,
                        is_favorite=False
                    )
                    db.session.add(user_container_state)
                user_container_state.last_accessed = func.now()
                db.session.commit()
                print(f">>> ROUTES: Đã cập nhật last_accessed cho bộ thẻ {s_id} <<<")
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Lỗi khi cập nhật last_accessed cho bộ thẻ {s_id}: {e}", exc_info=True)


    result = session_manager.process_flashcard_answer(item_id, user_answer)
    if 'error' in result:
        current_app.logger.error(f"Lỗi trong quá trình process_flashcard_answer: {result.get('error')}")
        return jsonify(result), 400

    session['flashcard_session'] = session_manager.to_dict()

    current_app.logger.debug("--- Kết thúc submit_flashcard_answer (Thành công) ---")
    return jsonify(result)


@flashcard_learning_bp.route('/end_session_flashcard', methods=['POST'])
@login_required
def end_session_flashcard():
    """
    Kết thúc phiên học Flashcard hiện tại.
    """
    current_app.logger.debug("--- Bắt đầu end_session_flashcard ---")
    result = FlashcardSessionManager.end_flashcard_session()
    current_app.logger.info(f"Phiên học Flashcard cho người dùng {current_user.user_id} đã kết thúc theo yêu cầu. Kết quả: {result.get('message')}")
    current_app.logger.debug("--- Kết thúc end_session_flashcard ---")
    return jsonify(result)


@flashcard_learning_bp.route('/save_flashcard_settings', methods=['POST'])
@login_required
def save_flashcard_settings():
    """
    Lưu cài đặt số thẻ mặc định trong một phiên học Flashcard của người dùng.
    Lưu ý: Không còn cần thiết vì Flashcard luôn dùng batch_size=1
    """
    flash('Cài đặt số thẻ mặc định không áp dụng cho Flashcard.', 'info')
    return jsonify({'success': False, 'message': 'Không áp dụng.'}), 400


@flashcard_learning_bp.route('/get_flashcard_sets_partial', methods=['GET'])
@login_required
def get_flashcard_sets_partial():
    """
    Trả về partial HTML chứa danh sách các bộ Flashcard, có hỗ trợ tìm kiếm và phân trang.
    """
    current_app.logger.debug(">>> Bắt đầu thực thi get_flashcard_sets_partial <<<")
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)
    current_filter = request.args.get('filter', 'doing', type=str)

    try:
        pagination = get_filtered_flashcard_sets(
            user_id=current_user.user_id,
            search_query=search_query,
            search_field=search_field,
            current_filter=current_filter,
            per_page=current_app.config['ITEMS_PER_PAGE'],
            page=page
        )
        flashcard_sets = pagination.items

        template_vars = {
            'flashcard_sets': flashcard_sets,
            'pagination': pagination,
            'search_query': search_query,
            'search_field': search_field,
            'search_options_display': {
                'title': 'Tiêu đề', 'description': 'Mô tả', 'tags': 'Thẻ'
            },
            'current_filter': current_filter
        }

        current_app.logger.debug("<<< Kết thúc thực thi get_flashcard_sets_partial (Thành công) >>>")
        return render_template('_flashcard_sets_selection.html', **template_vars)

    except Exception as e:
        print(f">>> PYTHON LỖI: Đã xảy ra lỗi trong get_flashcard_sets_partial: {e}")
        print(traceback.format_exc())
        current_app.logger.error(f"LỖI NGHIÊM TRỌNG khi tải danh sách bộ thẻ qua AJAX: {e}", exc_info=True)
        current_app.logger.debug("<<< Kết thúc thực thi get_flashcard_sets_partial (LỖI) >>>")
        return '<p class="text-red-500 text-center py-4">Đã xảy ra lỗi khi tải danh sách bộ thẻ. Vui lòng thử lại.</p>', 500


@flashcard_learning_bp.route('/toggle_archive_flashcard/<int:set_id>', methods=['POST'])
@login_required
def toggle_archive_flashcard(set_id):
    """
    Xử lý yêu cầu archive hoặc unarchive một bộ thẻ.
    """
    try:
        user_container_state = UserContainerState.query.filter_by(
            user_id=current_user.user_id,
            container_id=set_id
        ).first()

        is_currently_archived = False
        if user_container_state:
            user_container_state.is_archived = not user_container_state.is_archived
            is_currently_archived = user_container_state.is_archived
        else:
            user_container_state = UserContainerState(
                user_id=current_user.user_id,
                container_id=set_id,
                is_archived=True,
                is_favorite=False
            )
            db.session.add(user_container_state)
            is_currently_archived = True

        db.session.commit()
        
        status_text = "đã được lưu trữ." if is_currently_archived else "đã được bỏ lưu trữ."
        flash(f'Bộ thẻ "{set_id}" {status_text}', 'success')

        return jsonify({'success': True, 'is_archived': is_currently_archived, 'message': f'Bộ thẻ {status_text}'})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi khi toggle archive cho bộ thẻ {set_id}: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi khi thay đổi trạng thái lưu trữ.'}), 500


@flashcard_learning_bp.route('/bulk_unarchive_flashcard', methods=['POST'])
@login_required
def bulk_unarchive_flashcard():
    """
    Xử lý yêu cầu bỏ lưu trữ hàng loạt cho các bộ thẻ đã chọn.
    """
    data = request.get_json()
    set_ids = data.get('set_ids')
    
    if not set_ids or not isinstance(set_ids, list):
        return jsonify({'success': False, 'message': 'Dữ liệu không hợp lệ.'}), 400

    try:
        updated_count = 0
        for set_id in set_ids:
            user_container_state = UserContainerState.query.filter_by(
                user_id=current_user.user_id,
                container_id=set_id
            ).first()
            if user_container_state and user_container_state.is_archived:
                user_container_state.is_archived = False
                updated_count += 1
        
        db.session.commit()
        
        if updated_count > 0:
            flash(f'Đã bỏ lưu trữ thành công {updated_count} bộ thẻ.', 'success')
            return jsonify({'success': True, 'message': f'Đã bỏ lưu trữ thành công {updated_count} bộ thẻ.'})
        else:
            return jsonify({'success': False, 'message': 'Không có bộ thẻ nào được bỏ lưu trữ.'}), 400
    
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi khi bỏ lưu trữ hàng loạt: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi khi xử lý yêu cầu.'}), 500
