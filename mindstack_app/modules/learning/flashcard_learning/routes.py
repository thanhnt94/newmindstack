# File: mindstack_app/modules/learning/flashcard_learning/routes.py
# Phiên bản: 3.7
# MỤC ĐÍCH: Cập nhật logic để hỗ trợ chế độ học mới "Học và ôn tập (đan xen)".
# ĐÃ SỬA: Sửa đổi hàm start_new_flashcard_session để gọi đúng thuật toán mới.
# ĐÃ SỬA: Sửa lỗi truyền tham số trong get_flashcard_options_partial để tránh lỗi IndexError.
# ĐÃ SỬA: Bổ sung logic để lấy thuật toán `get_mixed_items`.

from flask import Blueprint, render_template, request, jsonify, abort, current_app, redirect, url_for, flash, session
from flask_login import login_required, current_user
import traceback
from .algorithms import get_new_only_items, get_due_items, get_hard_items, get_mixed_items, get_filtered_flashcard_sets, get_flashcard_mode_counts
from .session_manager import FlashcardSessionManager
from .config import FlashcardLearningConfig
from ....models import db, User, FlashcardProgress, UserContainerState, LearningContainer, LearningItem
from sqlalchemy.sql import func
import asyncio
from .audio_service import AudioService
from .image_service import ImageService
from sqlalchemy.orm.attributes import flag_modified
import os

flashcard_learning_bp = Blueprint('flashcard_learning', __name__,
                                  template_folder='templates')

audio_service = AudioService()
image_service = ImageService()


@flashcard_learning_bp.route('/flashcard_learning_dashboard')
@login_required
def flashcard_learning_dashboard():
    """
    Hiển thị trang chính để chọn bộ thẻ và chế độ học Flashcard.
    """
    search_query = request.args.get('q', '', type=str)
    search_field = request.args.get('search_field', 'all', type=str)
    current_filter = request.args.get('filter', 'doing', type=str)
    
    user_button_count = current_user.flashcard_button_count if current_user.flashcard_button_count else 3

    flashcard_set_search_options = {
        'title': 'Tiêu đề', 'description': 'Mô tả', 'tags': 'Thẻ'
    }

    template_vars = {
        'search_query': search_query,
        'search_field': search_field,
        'flashcard_set_search_options': flashcard_set_search_options,
        'current_filter': current_filter,
        'user_button_count': user_button_count
    }
    return render_template('flashcard_learning_dashboard.html', **template_vars)


@flashcard_learning_bp.route('/get_flashcard_options_partial/<set_identifier>', methods=['GET'])
@login_required
def get_flashcard_options_partial(set_identifier):
    """
    Trả về partial HTML chứa các chế độ học và số nút đánh giá tương ứng.
    """
    selected_mode = request.args.get('selected_mode', None, type=str)
    user_button_count = current_user.flashcard_button_count if current_user.flashcard_button_count else 3
    
    modes = []
    
    if set_identifier == 'all':
        modes = get_flashcard_mode_counts(current_user.user_id, 'all')
    else:
        try:
            set_ids = [int(s) for s in set_identifier.split(',') if s]
            if len(set_ids) == 1:
                # THAY ĐỔI: Lấy phần tử đầu tiên của danh sách
                modes = get_flashcard_mode_counts(current_user.user_id, set_ids[0])
            else:
                modes = get_flashcard_mode_counts(current_user.user_id, set_ids)
        except ValueError:
            return '<p class="text-red-500 text-center">Lỗi: Định dạng ID bộ thẻ không hợp lệ.</p>', 400
        except IndexError:
            return '<p class="text-red-500 text-center">Lỗi: Không tìm thấy ID bộ thẻ.</p>', 400


    return render_template('_flashcard_modes_selection.html',
                           modes=modes,
                           selected_set_id=set_identifier,
                           selected_flashcard_mode_id=selected_mode,
                           user_button_count=user_button_count
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
        flash('Không có bộ thẻ nào khả dụng để bắt đầu phiên học.', 'warning')
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
        flash('Không có bộ thẻ nào khả dụng để bắt đầu phiên học.', 'warning')
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
        flash('Không có bộ thẻ nào khả dụng để bắt đầu phiên học.', 'warning')
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

    user_button_count = current_user.flashcard_button_count if current_user.flashcard_button_count else 3
    session_data = session.get('flashcard_session', {})
    session_mode = session_data.get('mode')
    is_autoplay_session = session_mode in ('autoplay_all', 'autoplay_learned')
    autoplay_mode = session_mode if is_autoplay_session else ''

    return render_template(
        'flashcard_session.html',
        user_button_count=user_button_count,
        is_autoplay_session=is_autoplay_session,
        autoplay_mode=autoplay_mode
    )


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
        flashcard_batch = session_manager.get_next_batch()
        
        session['flashcard_session'] = session_manager.to_dict()
        session.modified = True

        if flashcard_batch is None:
            session_manager.end_flashcard_session()
            current_app.logger.info(f"Phiên học Flashcard cho người dùng {current_user.user_id} đã kết thúc do hết thẻ.")
            current_app.logger.debug("--- Kết thúc get_flashcard_batch (Hết thẻ) ---")
            return jsonify({'message': 'Bạn đã hoàn thành tất cả các thẻ trong phiên học này!'}), 404
        
        flashcard_batch['session_correct_answers'] = session_manager.correct_answers
        flashcard_batch['session_incorrect_answers'] = session_manager.incorrect_answers
        flashcard_batch['session_vague_answers'] = session_manager.vague_answers
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
    Nhận câu trả lời của người dùng, xử lý và cập nhật tiến độ.
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
                
    user_button_count = current_user.flashcard_button_count or 3
    normalized_answer = str(user_answer).lower()

    if normalized_answer == 'continue':
        user_answer_quality = None
    else:
        quality_map = {}

        # SỬA ĐỔI: Ánh xạ các nút về thang điểm 0-5
        if user_button_count == 3:
            quality_map = {'quên': 0, 'mơ_hồ': 3, 'nhớ': 5}
        elif user_button_count == 4:
            quality_map = {'again': 0, 'hard': 1, 'good': 3, 'easy': 5}
        elif user_button_count == 6:
            quality_map = {'fail': 0, 'very_hard': 1, 'hard': 2, 'medium': 3, 'good': 4, 'very_easy': 5}

        user_answer_quality = quality_map.get(normalized_answer, 0)

    result = session_manager.process_flashcard_answer(item_id, user_answer_quality)
    if 'error' in result:
        current_app.logger.error(f"Lỗi trong quá trình process_flashcard_answer: {result.get('error')}")
        return jsonify(result), 400

    session['flashcard_session'] = session_manager.to_dict()

    response_data = {
        'success': True,
        'score_change': result.get('score_change'),
        'updated_total_score': result.get('updated_total_score'),
        'is_correct': result.get('is_correct'),
        'new_progress_status': result.get('new_progress_status'),
        'statistics': result.get('statistics'),
        'session_correct_answers': session_manager.correct_answers,
        'session_incorrect_answers': session_manager.incorrect_answers,
        'session_vague_answers': session_manager.vague_answers,
        'session_total_answered': session_manager.correct_answers + session_manager.incorrect_answers + session_manager.vague_answers
    }

    current_app.logger.debug("--- Kết thúc submit_flashcard_answer (Thành công) ---")
    return jsonify(response_data)


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
    Lưu cài đặt số nút đánh giá mặc định trong một phiên học Flashcard của người dùng.
    """
    data = request.get_json()
    button_count = data.get('button_count')

    if button_count is None or not isinstance(button_count, int) or button_count not in [3, 4, 6]:
        return jsonify({'success': False, 'message': 'Số nút đánh giá không hợp lệ.'}), 400

    try:
        user = User.query.get(current_user.user_id)
        if user:
            user.flashcard_button_count = button_count
            db.session.commit()
            return jsonify({'success': True, 'message': 'Cài đặt số nút đã được lưu.'})
        else:
            return jsonify({'success': False, 'message': 'Không tìm thấy người dùng.'}), 404
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi khi lưu cài đặt Flashcard của người dùng: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi khi lưu cài đặt.'}), 500


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


@flashcard_learning_bp.route('/generate-image-from-content', methods=['POST'])
@login_required
def generate_image_from_content():
    """Tự động tìm và lưu ảnh minh họa dựa trên nội dung của thẻ."""
    data = request.get_json(silent=True) or {}
    item_id = data.get('item_id')
    side = (data.get('side') or 'front').lower()

    if not item_id:
        return jsonify({'success': False, 'message': 'Thiếu thông tin mã thẻ.'}), 400

    if side not in {'front', 'back'}:
        return jsonify({'success': False, 'message': 'Mặt thẻ không hợp lệ.'}), 400

    item = LearningItem.query.get(item_id)
    if not item or item.item_type != 'FLASHCARD':
        return jsonify({'success': False, 'message': 'Không tìm thấy thẻ phù hợp.'}), 404

    content = item.content or {}
    text_source = content.get('front' if side == 'front' else 'back') or ''
    if not str(text_source).strip():
        return jsonify({'success': False, 'message': 'Không có nội dung để tìm ảnh minh họa.'}), 400

    try:
        absolute_path, success, message = image_service.get_cached_or_download_image(str(text_source))
        if success and absolute_path:
            relative_path = image_service.convert_to_static_url(absolute_path)
            if not relative_path:
                return jsonify({'success': False, 'message': 'Không thể lưu đường dẫn ảnh.'}), 500

            if side == 'front':
                content['front_img'] = relative_path
            else:
                content['back_img'] = relative_path

            item.content = content
            flag_modified(item, 'content')
            db.session.commit()

            return jsonify({
                'success': True,
                'message': 'Đã cập nhật ảnh minh họa thành công.',
                'image_url': url_for('static', filename=relative_path)
            })

        return jsonify({'success': False, 'message': message or 'Không tìm thấy ảnh phù hợp.'}), 500
    except Exception as exc:  # pylint: disable=broad-except
        db.session.rollback()
        current_app.logger.error(f"Lỗi khi tạo ảnh minh họa cho thẻ {item_id}: {exc}", exc_info=True)
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi khi xử lý yêu cầu.'}), 500

@flashcard_learning_bp.route('/regenerate-audio-from-content', methods=['POST'])
@login_required
def regenerate_audio_from_content():
    """
    Kích hoạt việc tạo file audio từ nội dung văn bản và lưu đường dẫn vào database.
    """
    data = request.get_json()
    item_id = data.get('item_id')
    side = data.get('side')
    content_to_read = data.get('content_to_read')

    if not item_id or not side or not content_to_read:
        return jsonify({'success': False, 'message': 'Dữ liệu không hợp lệ.'}), 400

    item = LearningItem.query.get(item_id)
    if not item or item.item_type != 'FLASHCARD':
        return jsonify({'success': False, 'message': 'Không tìm thấy thẻ hoặc loại thẻ không đúng.'}), 404

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        path_or_url, success, msg = loop.run_until_complete(audio_service.get_cached_or_generate_audio(content_to_read))
        if success:
            relative_path = os.path.relpath(path_or_url, current_app.static_folder)
            relative_path = relative_path.replace(os.path.sep, '/')

            if side == 'front':
                item.content['front_audio_url'] = relative_path
            elif side == 'back':
                item.content['back_audio_url'] = relative_path
            
            flag_modified(item, 'content')
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Đã tạo audio thành công.',
                'audio_url': url_for('static', filename=relative_path)
            })
        else:
            return jsonify({'success': False, 'message': msg}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Lỗi khi tạo audio từ nội dung: {e}", exc_info=True)
        return jsonify({'success': False, 'message': 'Đã xảy ra lỗi khi xử lý yêu cầu.'}), 500
    finally:
        loop.close()