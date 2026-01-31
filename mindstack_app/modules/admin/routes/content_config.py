from flask import render_template, request, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from mindstack_app.models import User, AppSettings, db
from mindstack_app.core.defaults import DEFAULT_APP_CONFIGS
from .. import blueprint

def _get_setting_obj(key, description, data_type='int'):
    """Helper to build setting object for template."""
    # Fetch from DB first, then Default
    val = AppSettings.get(key, DEFAULT_APP_CONFIGS.get(key))
    default_val = DEFAULT_APP_CONFIGS.get(key)
    
    return {
        'key': key,
        'description': description,
        'data_type': data_type,
        'value': val,
        'default': default_val
    }

@blueprint.route('/content-config', methods=['GET'])
@login_required
def content_config_page():
    """
    Page to manage content-related settings (Quiz & Flashcard).
    """
    if current_user.user_role != User.ROLE_ADMIN:
        flash('Permission denied', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    # --- Construct General Settings ---
    general_settings = {
        'uploads': {
            'label': 'Tải lên & Lưu trữ',
            'icon': 'fas fa-cloud-upload-alt',
            'settings': [
                _get_setting_obj('CONTENT_MAX_UPLOAD_SIZE', 'Kích thước file tối đa (MB)', 'int'),
                _get_setting_obj('CONTENT_ALLOWED_EXTENSIONS', 'Định dạng file cho phép', 'string'),
            ]
        },
        'access': {
            'label': 'Quyền truy cập & Chia sẻ',
            'icon': 'fas fa-share-alt',
            'settings': [
                _get_setting_obj('CONTENT_ENABLE_PUBLIC_SHARING', 'Cho phép chia sẻ công khai (Public Sharing)', 'json'),
            ]
        }
    }

    # --- Construct Quiz Settings ---
    quiz_settings = {
        'scoring': {
            'label': 'Điểm thưởng (Gamification)',
            'icon': 'fas fa-star',
            'settings': [
                _get_setting_obj('QUIZ_FIRST_TIME_BONUS', 'Điểm thưởng khi hoàn thành Quiz lần đầu'),
                _get_setting_obj('QUIZ_CORRECT_BONUS', 'Điểm thưởng cho mỗi câu đúng'),
            ]
        },
        'vocab_games': {
             'label': 'Minigame Từ vựng',
             'icon': 'fas fa-gamepad',
             'settings': [
                 _get_setting_obj('VOCAB_MCQ_CORRECT_BONUS', 'Điểm: Trắc nghiệm (MCQ)'),
                 _get_setting_obj('VOCAB_TYPING_CORRECT_BONUS', 'Điểm: Gõ từ (Typing)'),
                 _get_setting_obj('VOCAB_MATCHING_CORRECT_BONUS', 'Điểm: Nối từ (Matching)'),
                 _get_setting_obj('VOCAB_LISTENING_CORRECT_BONUS', 'Điểm: Nghe (Listening)'),
                 _get_setting_obj('VOCAB_SPEED_CORRECT_BONUS', 'Điểm: Tốc độ (Speed Review)'),
             ]
        }
    }

    # --- Construct Flashcard Settings ---
    flashcard_settings = {
        'fsrs_params': {
            'label': 'Tham số FSRS (Thuật toán lặp lại)',
            'icon': 'fas fa-brain',
            'settings': [
                _get_setting_obj('FSRS_DESIRED_RETENTION', 'Tỷ lệ nhớ mong muốn (0.7 - 0.99)', 'float'),
                _get_setting_obj('FSRS_MAX_INTERVAL', 'Khoảng cách lặp lại tối đa (ngày)', 'int'),
                _get_setting_obj('FSRS_ENABLE_FUZZ', 'Bật ngẫu nhiên hóa thời gian (Fuzzing) [true/false]', 'json'),
            ]
        },
        'fsrs_scoring': {
            'label': 'Điểm số Flashcard (XP)',
            'icon': 'fas fa-trophy',
            'settings': [
                _get_setting_obj('SCORE_FSRS_AGAIN', 'Điểm khi chọn: Quên (Again)'),
                _get_setting_obj('SCORE_FSRS_HARD', 'Điểm khi chọn: Khó (Hard)'),
                _get_setting_obj('SCORE_FSRS_GOOD', 'Điểm khi chọn: Tốt (Good)'),
                _get_setting_obj('SCORE_FSRS_EASY', 'Điểm khi chọn: Dễ (Easy)'),
            ]
        }
    }

    return render_template('admin/content_config.html', 
                           general_settings=general_settings,
                           quiz_settings=quiz_settings,
                           flashcard_settings=flashcard_settings,
                           active_page='content_config')

@blueprint.route('/content-config/save-general', methods=['POST'])
@login_required
def save_general_config():
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    data = request.get_json()
    settings = data.get('settings', {})
    
    try:
        for key, val in settings.items():
            AppSettings.set(key, val, category='content') 
        db.session.commit()
        return jsonify({'success': True, 'message': 'Đã lưu cấu hình chung.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@blueprint.route('/content-config/reset-general', methods=['POST'])
@login_required
def reset_general_config():
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
    keys_to_reset = ['CONTENT_MAX_UPLOAD_SIZE', 'CONTENT_ALLOWED_EXTENSIONS', 'CONTENT_ENABLE_PUBLIC_SHARING']
    
    try:
        for k in keys_to_reset:
            setting = AppSettings.query.get(k)
            if setting:
                db.session.delete(setting)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Đã khôi phục mặc định chung.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@blueprint.route('/content-config/save-quiz', methods=['POST'])
@login_required
def save_quiz_config():
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    data = request.get_json()
    settings = data.get('settings', {})
    
    try:
        for key, val in settings.items():
            AppSettings.set(key, val, category='scoring') 
        db.session.commit()
        return jsonify({'success': True, 'message': 'Đã lưu cấu hình Quiz.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@blueprint.route('/content-config/save-flashcard', methods=['POST'])
@login_required
def save_flashcard_config():
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    data = request.get_json()
    settings = data.get('settings', {})
    
    try:
        for key, val in settings.items():
            AppSettings.set(key, val, category='srs')
        db.session.commit()
        return jsonify({'success': True, 'message': 'Đã lưu cấu hình Flashcard/FSRS.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@blueprint.route('/content-config/reset-quiz', methods=['POST'])
@login_required
def reset_quiz_config():
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
    keys_to_reset = [
        'QUIZ_FIRST_TIME_BONUS', 'QUIZ_CORRECT_BONUS',
        'VOCAB_MCQ_CORRECT_BONUS', 'VOCAB_TYPING_CORRECT_BONUS',
        'VOCAB_MATCHING_CORRECT_BONUS', 'VOCAB_LISTENING_CORRECT_BONUS',
        'VOCAB_SPEED_CORRECT_BONUS'
    ]
    
    try:
        for k in keys_to_reset:
            setting = AppSettings.query.get(k)
            if setting:
                db.session.delete(setting)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Đã khôi phục mặc định Quiz.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@blueprint.route('/content-config/reset-flashcard', methods=['POST'])
@login_required
def reset_flashcard_config():
    if current_user.user_role != User.ROLE_ADMIN:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
        
    keys_to_reset = [
        'FSRS_DESIRED_RETENTION', 'FSRS_MAX_INTERVAL', 'FSRS_ENABLE_FUZZ',
        'SCORE_FSRS_AGAIN', 'SCORE_FSRS_HARD', 'SCORE_FSRS_GOOD', 'SCORE_FSRS_EASY'
    ]
    
    try:
        for k in keys_to_reset:
            setting = AppSettings.query.get(k)
            if setting:
                db.session.delete(setting)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Đã khôi phục mặc định Flashcard.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500