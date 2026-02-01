# File: mindstack_app/modules/admin/routes/views.py
from flask import render_template, redirect, url_for, flash, request, current_app, abort, jsonify
from flask_login import current_user, login_user, logout_user
from sqlalchemy import nullslast
from sqlalchemy.orm.attributes import flag_modified
from datetime import datetime, timedelta
import os
from uuid import uuid4
from werkzeug.utils import secure_filename, safe_join

from mindstack_app.core.config import Config
from mindstack_app.core.module_registry import DEFAULT_MODULES
from mindstack_app.core.defaults import DEFAULT_APP_CONFIGS
from mindstack_app.services.config_service import get_runtime_config
from mindstack_app.services.template_service import TemplateService
from mindstack_app.models import (
    db, User, LearningContainer, LearningItem, ApiKey, BackgroundTask, BackgroundTaskLog,
    AppSettings, UserContainerState, LearningProgress, Note, ScoreLog, Feedback as UserFeedback
)
from mindstack_app.utils.pagination import get_pagination_data
from mindstack_app.modules.content_management.forms import CourseForm, FlashcardSetForm, QuizSetForm
from mindstack_app.modules.content_management.services.kernel_service import ContentKernelService
from mindstack_app.modules.AI.services.explanation_service import DEFAULT_REQUEST_INTERVAL_SECONDS

from .. import admin_bp as blueprint
from ..context_processors import build_admin_sidebar_metrics
from ..forms import AdminLoginForm
from ..services.settings_service import (
    CORE_SETTING_KEYS, CORE_SETTING_FIELDS, SETTING_CATEGORY_LABELS,
    is_sensitive_setting, get_core_settings, get_grouped_core_settings,
    categorize_settings, refresh_runtime_settings, log_setting_change,
    parse_setting_value, validate_setting_value
)
from ..services.media_service import (
    ADMIN_ALLOWED_MEDIA_EXTENSIONS, normalize_subpath,
    collect_directory_listing, format_file_size
)

# --- Auth Routes ---

@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    """Separate login route for Administrators."""
    if current_user.is_authenticated:
        if current_user.user_role == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        
        logout_user()
        flash('Đã đăng xuất tài khoản thường. Vui lòng đăng nhập Admin.', 'info')
    
    form = AdminLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Admin ID hoặc Security Key không đúng.', 'danger')
            return redirect(url_for('admin.login'))
        
        if user.user_role != 'admin':
            flash('Truy cập bị từ chối: Tài khoản này không có quyền Quản trị.', 'danger')
            return redirect(url_for('admin.login'))
        
        login_user(user, remember=form.remember_me.data)
        
        try:
            from mindstack_app.modules.gamification.services.scoring_service import ScoreService
            ScoreService.record_daily_login(user.user_id)
        except Exception:
            pass

        flash('Chào mừng Quản trị viên! Đã truy cập hệ thống an toàn.', 'success')
        next_page = request.args.get('next')
        if not next_page or next_page == url_for('landing.index'):
             next_page = url_for('admin.admin_dashboard')
        return redirect(next_page)
        
    return render_template('admin/modules/admin/login.html', form=form)

# --- Dashboard View ---

@blueprint.route('/')
@blueprint.route('/dashboard')
def admin_dashboard():
    """
    Mô tả: Hiển thị trang dashboard admin tổng quan.
    """
    total_users = db.session.query(User).count()
    users_last_24h = db.session.query(User).filter(User.last_seen >= (datetime.utcnow() - timedelta(hours=24))).count()
    
    total_containers = db.session.query(LearningContainer).count()
    total_items = db.session.query(LearningItem).count()
    
    active_api_keys = db.session.query(ApiKey).filter_by(is_active=True, is_exhausted=False).count()
    exhausted_api_keys = db.session.query(ApiKey).filter_by(is_exhausted=True).count()
    
    stats_data = {
        'total_users': total_users,
        'users_last_24h': users_last_24h,
        'total_containers': total_containers,
        'total_items': total_items,
        'active_api_keys': active_api_keys,
        'exhausted_api_keys': exhausted_api_keys
    }

    recent_users = (
        User.query.filter(User.last_seen.isnot(None))
        .order_by(User.last_seen.desc())
        .limit(5)
        .all()
    )

    recent_containers = (
        LearningContainer.query.order_by(LearningContainer.created_at.desc())
        .limit(5)
        .all()
    )

    recent_tasks = (
        BackgroundTask.query.order_by(nullslast(BackgroundTask.last_updated.desc()))
        .limit(4)
        .all()
    )

    overview_metrics = build_admin_sidebar_metrics()

    return render_template(
        'admin/modules/admin/dashboard.html',
        stats_data=stats_data,
        recent_users=recent_users,
        recent_containers=recent_containers,
        recent_tasks=recent_tasks,
        overview_metrics=overview_metrics,
    )

# --- Module Management Views ---

@blueprint.route('/modules', methods=['GET'])
def manage_modules():
    """Hiển thị danh sách các modules và trạng thái bật/tắt."""
    modules_data = []
    for mod in DEFAULT_MODULES:
        is_core = mod.config_key in ['admin', 'auth', 'landing']
        is_active = AppSettings.get(f"MODULE_ENABLED_{mod.config_key}", True) if not is_core else True
        
        modules_data.append({
            'key': mod.config_key,
            'name': mod.display_name or mod.config_key,
            'import_path': mod.import_path,
            'is_active': is_active,
            'is_core': is_core
        })

    return render_template('admin/modules/admin/manage_modules.html', 
                           modules=modules_data, 
                           active_page='modules')

# --- Template Management Views ---

@blueprint.route('/templates', methods=['GET'])
def manage_templates():
    """
    Page to manage system themes and templates.
    """
    # Fetch structured settings compatible with the template
    template_settings = TemplateService.get_all_template_settings()

    return render_template('admin/modules/admin/manage_templates.html', 
                           template_settings=template_settings,
                           active_page='templates')

# --- Content Configuration Views ---

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
def content_config_page():
    """
    Page to manage GENERAL content settings (Uploads, Access).
    """
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

    return render_template('admin/modules/admin/content_config.html', 
                           general_settings=general_settings,
                           active_page='content_config')

# --- Background Task Views ---

@blueprint.route('/tasks')
def manage_background_tasks():
    """
    Mô tả: Hiển thị trang quản lý các tác vụ nền.
    """
    tasks = BackgroundTask.query.all()
    desired_tasks = [
        'generate_audio_cache',
        'clean_audio_cache',
        'generate_image_cache',
        'clean_image_cache',
        'generate_ai_explanations'
    ]
    created_any = False
    for task_name in desired_tasks:
        if not BackgroundTask.query.filter_by(task_name=task_name).first():
            db.session.add(BackgroundTask(task_name=task_name, message='Sẵn sàng', is_enabled=True))
            created_any = True
    if created_any:
        db.session.commit()
        tasks = BackgroundTask.query.all()

    flashcard_containers = (
        LearningContainer.query.filter_by(container_type='FLASHCARD_SET')
        .order_by(LearningContainer.title.asc())
        .all()
    )
    quiz_containers = (
        LearningContainer.query.filter_by(container_type='QUIZ_SET')
        .order_by(LearningContainer.title.asc())
        .all()
    )

    return render_template(
        'admin/modules/admin/background_tasks.html',
        tasks=tasks,
        flashcard_containers=flashcard_containers,
        quiz_containers=quiz_containers,
        default_request_interval=DEFAULT_REQUEST_INTERVAL_SECONDS,
    )

@blueprint.route('/tasks/<int:task_id>/logs', methods=['GET'])
def view_task_logs(task_id: int):
    task = BackgroundTask.query.get_or_404(task_id)
    logs = (
        BackgroundTaskLog.query.filter_by(task_id=task_id)
        .order_by(BackgroundTaskLog.created_at.desc())
        .limit(200)
        .all()
    )

    return render_template(
        'admin/modules/admin/background_task_logs.html',
        task=task,
        logs=logs,
    )

# --- Content Management Views ---

@blueprint.route('/content/', methods=['GET'])
def content_dashboard():
    """
    Admin Content Dashboard.
    Overview of all content in the system.
    """
    # Statistics
    stats = {
        'total_courses': LearningContainer.query.filter_by(container_type='COURSE').count(),
        'total_flashcards': LearningContainer.query.filter_by(container_type='FLASHCARD_SET').count(),
        'total_quizzes': LearningContainer.query.filter_by(container_type='QUIZ_SET').count(),
    }

    return render_template('admin/modules/admin/content/dashboard.html', stats=stats, active_page='content')

@blueprint.route('/content/list/<container_type>/', methods=['GET'])
def list_content(container_type):
    container_type = container_type.upper()
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '')

    query = LearningContainer.query.filter_by(container_type=container_type)
    
    if search:
        query = query.filter(LearningContainer.title.ilike(f'%{search}%'))

    pagination = get_pagination_data(query.order_by(LearningContainer.created_at.desc()), page)
    
    return render_template('admin/modules/admin/content/list.html', 
                           containers=pagination.items, 
                           pagination=pagination,
                           container_type=container_type,
                           active_page='content')

def _get_form_for_type(container_type):
    forms = {
        'COURSE': CourseForm,
        'FLASHCARD_SET': FlashcardSetForm,
        'QUIZ_SET': QuizSetForm
    }
    return forms.get(container_type.upper())

@blueprint.route('/content/edit/<int:container_id>', methods=['GET', 'POST'])
def edit_content(container_id):
    container = LearningContainer.query.get_or_404(container_id)
    form_class = _get_form_for_type(container.container_type)
    if not form_class:
        abort(404, description="Unknown container type")

    form = form_class(obj=container)
    
    if form.validate_on_submit():
        try:
            update_data = {
                'title': form.title.data,
                'description': getattr(form, 'description', None) and form.description.data,
                'cover_image': getattr(form, 'cover_image', None) and form.cover_image.data,
                'tags': getattr(form, 'tags', None) and form.tags.data,
                'is_public': getattr(form, 'is_public', None) and form.is_public.data,
                'ai_prompt': getattr(form, 'ai_prompt', None) and form.ai_prompt.data,
            }
            
            # Map media folders if present
            if hasattr(form, 'image_base_folder'):
                update_data['media_image_folder'] = form.image_base_folder.data
            if hasattr(form, 'audio_base_folder'):
                update_data['media_audio_folder'] = form.audio_base_folder.data

            ContentKernelService.update_container(container_id, **update_data)
            
            flash('Đã cập nhật thành công!', 'success')
            return redirect(url_for('admin.list_content', container_type=container.container_type.lower()))
        except Exception as e:
            db.session.rollback()
            flash(f'Lỗi khi cập nhật: {str(e)}', 'danger')

    return render_template('admin/modules/admin/content/edit.html', form=form, container=container, active_page='content')

# --- Media Library Views ---

@blueprint.route('/media-library', methods=['GET', 'POST'])
def media_library():
    """
    Mô tả: Hiển thị trang quản lý thư viện media (tải file, tạo thư mục).
    """
    upload_root = get_runtime_config('UPLOAD_FOLDER', Config.UPLOAD_FOLDER)
    if not upload_root:
        flash('Hệ thống chưa cấu hình thư mục lưu trữ uploads.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    try:
        current_folder = normalize_subpath(
            request.form.get('current_folder') if request.method == 'POST' else request.args.get('folder')
        )
    except ValueError:
        flash('Đường dẫn thư mục không hợp lệ.', 'danger')
        return redirect(url_for('admin.media_library'))

    target_dir = safe_join(upload_root, current_folder) if current_folder else upload_root
    if target_dir is None:
        flash('Đường dẫn thư mục không hợp lệ.', 'danger')
        return redirect(url_for('admin.media_library'))

    os.makedirs(target_dir, exist_ok=True)

    if request.method == 'POST':
        action = request.form.get('action', 'upload')
        if action == 'create_folder':
            new_folder_name = secure_filename(request.form.get('folder_name', '').strip())
            if not new_folder_name:
                flash('Tên thư mục không hợp lệ.', 'warning')
            else:
                new_dir = os.path.join(target_dir, new_folder_name)
                os.makedirs(new_dir, exist_ok=True)
                flash(f'Đã tạo thư mục "{new_folder_name}".', 'success')
                normalized_new_dir = normalize_subpath(os.path.relpath(new_dir, upload_root))
                return redirect(url_for('admin.media_library', folder=normalized_new_dir))
        else:
            uploaded_files = request.files.getlist('media_files')
            if not uploaded_files:
                flash('Vui lòng chọn ít nhất một file để tải lên.', 'warning')
            else:
                saved = []
                skipped = []
                for file in uploaded_files:
                    if not file or file.filename == '':
                        continue
                    original_name = file.filename
                    filename = secure_filename(original_name)
                    if not filename:
                        skipped.append(original_name)
                        continue
                    ext = os.path.splitext(filename)[1].lower()
                    if ext and ext not in ADMIN_ALLOWED_MEDIA_EXTENSIONS:
                        skipped.append(original_name)
                        continue

                    candidate_name = filename
                    destination = os.path.join(target_dir, candidate_name)
                    while os.path.exists(destination):
                        name_part, extension_part = os.path.splitext(filename)
                        candidate_name = f"{name_part}_{uuid4().hex[:6]}{extension_part}"
                        destination = os.path.join(target_dir, candidate_name)

                    try:
                        file.save(destination)
                        saved.append(candidate_name)
                    except Exception as exc:
                        current_app.logger.exception('Không thể lưu file %s: %s', candidate_name, exc)
                        skipped.append(original_name)

                if saved:
                    flash(f'Đã tải lên {len(saved)} file thành công.', 'success')
                if skipped:
                    flash('Một số file bị bỏ qua: ' + ', '.join(skipped), 'warning')

        return redirect(url_for('admin.media_library', folder=current_folder or None))

    directories, files = collect_directory_listing(target_dir, upload_root)
    breadcrumb = []
    if current_folder:
        parts = current_folder.split('/')
        cumulative = []
        for part in parts:
            cumulative.append(part)
            breadcrumb.append({'name': part, 'path': '/'.join(cumulative)})

    parent_folder = '/'.join(current_folder.split('/')[:-1]) if current_folder else ''
    total_size = format_file_size(sum(item['size_bytes'] for item in files)) if files else '0 B'

    return render_template(
        'admin/modules/admin/media_library.html',
        directories=directories,
        files=files,
        current_folder=current_folder,
        parent_folder=parent_folder,
        breadcrumb=breadcrumb,
        total_size=total_size,
    )

@blueprint.route('/media-library/delete', methods=['POST'])
def delete_media_item():
    """
    Mô tả: Xử lý yêu cầu xóa một file media.
    """
    upload_root = get_runtime_config('UPLOAD_FOLDER', Config.UPLOAD_FOLDER)
    if not upload_root:
        flash('Hệ thống chưa cấu hình thư mục lưu trữ uploads.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    try:
        relative_path = normalize_subpath(request.form.get('path'))
    except ValueError:
        flash('Đường dẫn file không hợp lệ.', 'danger')
        return redirect(url_for('admin.media_library'))

    full_path = safe_join(upload_root, relative_path)
    if not full_path or not os.path.isfile(full_path):
        flash('Không tìm thấy file để xóa.', 'warning')
        parent_folder = '/'.join((relative_path or '').split('/')[:-1])
        return redirect(url_for('admin.media_library', folder=parent_folder or None))

    try:
        os.remove(full_path)
        flash('Đã xóa file thành công.', 'success')
    except Exception as exc:
        current_app.logger.exception('Không thể xóa file %s: %s', full_path, exc)
        flash('Không thể xóa file. Vui lòng thử lại.', 'danger')

    parent_folder = '/'.join(relative_path.split('/')[:-1])
    return redirect(url_for('admin.media_library', folder=parent_folder or None))

# --- System Settings Views ---

@blueprint.route('/settings', methods=['GET', 'POST'])
def manage_system_settings():
    """
    Mô tả: Quản lý các cài đặt hệ thống.
    """
    telegram_token_setting = AppSettings.query.get('telegram_bot_token')

    raw_settings = AppSettings.query.order_by(AppSettings.key.asc()).all()
    
    def _is_gamification_setting(key: str) -> bool:
        key_upper = key.upper()
        return (
            key_upper.startswith('FLASHCARD_') or
            key_upper.startswith('QUIZ_') or
            key_upper.startswith('COURSE_') or
            key_upper.startswith('VOCAB_') or
            key_upper.startswith('DAILY_LOGIN') or
            'SCORE' in key_upper or
            'BONUS' in key_upper or
            'POINTS' in key_upper
        )
    
    settings = [
        setting
        for setting in raw_settings
        if not is_sensitive_setting(setting.key) 
           and setting.key not in CORE_SETTING_KEYS 
           and setting.key != 'telegram_bot_token'
           and not _is_gamification_setting(setting.key)
    ]
    data_type_options = ['string', 'int', 'bool', 'path', 'json']
    category_order = ['paths']

    users = User.query.order_by(User.username.asc()).all()
    quiz_sets = (
        LearningContainer.query.filter_by(container_type='QUIZ_SET')
        .order_by(LearningContainer.title.asc())
        .all()
    )

    return render_template(
        'admin/modules/admin/system_settings.html',
        telegram_token_setting=telegram_token_setting,
        core_settings=get_core_settings(),
        grouped_core_settings=get_grouped_core_settings(),
        settings_by_category=categorize_settings(settings),
        category_order=category_order,
        category_labels=SETTING_CATEGORY_LABELS,
        data_type_options=data_type_options,
        users=users,
        quiz_sets=quiz_sets
    )

@blueprint.route('/settings/telegram-token', methods=['POST'])
def save_telegram_token():
    """Lưu Telegram Bot Token."""
    token_value = (request.form.get('value') or '').strip()
    
    setting = AppSettings.query.get('telegram_bot_token')
    old_value = setting.value if setting else None

    if setting:
        setting.value = token_value
        setting.data_type = 'string'
        flag_modified(setting, 'value')
    else:
        setting = AppSettings(
            key='telegram_bot_token',
            value=token_value,
            category='telegram',
            data_type='string',
            description='Telegram Bot API Token để gửi tin nhắn nhắc nhở.'
        )
        db.session.add(setting)
    
    db.session.commit()
    log_setting_change(
        "update", key="telegram_bot_token", old_value=old_value, new_value=token_value
    )
    refresh_runtime_settings()
    flash('Telegram Bot Token đã được lưu thành công!', 'success')
    return redirect(url_for('admin.manage_system_settings'))


@blueprint.route('/settings/core', methods=['POST'])
def update_core_settings():
    """Cập nhật nhanh các cấu hình vận hành quan trọng."""
    updated_count = 0
    pending_logs: list[tuple[str, object, object]] = []

    for field in CORE_SETTING_FIELDS:
        key = field["key"]
        data_type = str(field.get("data_type", "string")).lower()
        description = field.get("description")
        raw_value = request.form.get(key)

        if raw_value is None:
            continue

        try:
            parsed_value = parse_setting_value(raw_value, data_type, key=key)
            validate_setting_value(parsed_value, data_type, key=key)
        except ValueError as exc:
            flash(str(exc), 'danger')
            return redirect(url_for('admin.manage_system_settings'))

        setting = AppSettings.query.get(key)
        old_value = setting.value if setting else None

        if setting:
            setting.value = parsed_value
            setting.data_type = data_type
            setting.description = description
            flag_modified(setting, 'value')
        else:
            setting = AppSettings(
                key=key,
                value=parsed_value,
                category='system',
                data_type=data_type,
                description=description,
            )
            db.session.add(setting)

        pending_logs.append((key, old_value, parsed_value))
        updated_count += 1

    if updated_count:
        db.session.commit()
        for key, old_value, parsed_value in pending_logs:
            log_setting_change("update", key=key, old_value=old_value, new_value=parsed_value)
        refresh_runtime_settings()
        flash('Đã lưu cấu hình vận hành.', 'success')
    else:
        flash('Không có thay đổi nào được ghi nhận.', 'info')

    return redirect(url_for('admin.manage_system_settings'))


@blueprint.route('/settings/create', methods=['POST'])
def create_system_setting():
    key = (request.form.get('key') or '').strip().upper()
    value = request.form.get('value')
    data_type = (request.form.get('data_type') or 'string').lower()
    description = (request.form.get('description') or '').strip() or None

    if not key:
        flash('Khóa cấu hình không được bỏ trống.', 'danger')
        return redirect(url_for('admin.manage_system_settings'))

    if is_sensitive_setting(key):
        flash('Khóa cấu hình này được bảo vệ.', 'warning')
        return redirect(url_for('admin.manage_system_settings'))

    if AppSettings.query.get(key):
        flash('Khóa cấu hình đã tồn tại.', 'warning')
        return redirect(url_for('admin.manage_system_settings'))

    try:
        parsed_value = parse_setting_value(value, data_type, key=key)
        validate_setting_value(parsed_value, data_type, key=key)
    except ValueError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('admin.manage_system_settings'))

    setting = AppSettings(key=key, value=parsed_value, category='system', data_type=data_type, description=description)
    db.session.add(setting)
    db.session.commit()

    log_setting_change("create", key=key, old_value=None, new_value=parsed_value)
    refresh_runtime_settings()
    flash('Đã thêm cấu hình mới thành công.', 'success')
    return redirect(url_for('admin.manage_system_settings'))


@blueprint.route('/settings/<string:setting_key>/update', methods=['POST'])
def update_system_setting(setting_key):
    setting = AppSettings.query.get_or_404(setting_key)

    if is_sensitive_setting(setting.key):
        flash('Khóa cấu hình này được bảo vệ.', 'danger')
        return redirect(url_for('admin.manage_system_settings'))

    data_type = (request.form.get('data_type') or setting.data_type or 'string').lower()
    description = (request.form.get('description') or '').strip() or None
    raw_value = request.form.get('value')

    try:
        parsed_value = parse_setting_value(raw_value, data_type, key=setting.key)
        validate_setting_value(parsed_value, data_type, key=setting.key)
    except ValueError as exc:
        flash(str(exc), 'danger')
        return redirect(url_for('admin.manage_system_settings'))

    setting.data_type = data_type
    setting.description = description
    old_value = setting.value
    setting.value = parsed_value
    flag_modified(setting, 'value')

    db.session.commit()
    log_setting_change(
        "update", key=setting.key, old_value=old_value, new_value=parsed_value
    )
    refresh_runtime_settings()
    flash('Đã cập nhật cấu hình thành công.', 'success')
    return redirect(url_for('admin.manage_system_settings'))


@blueprint.route('/settings/<string:setting_key>/delete', methods=['POST'])
def delete_system_setting(setting_key):
    setting = AppSettings.query.get_or_404(setting_key)

    if is_sensitive_setting(setting.key):
        flash('Không thể xóa khóa cấu hình được bảo vệ.', 'danger')
        return redirect(url_for('admin.manage_system_settings'))

    old_value = setting.value
    db.session.delete(setting)
    db.session.commit()

    current_app.config.pop(setting.key, None)
    log_setting_change("delete", key=setting.key, old_value=old_value, new_value=None)
    refresh_runtime_settings()

    flash('Đã xóa cấu hình.', 'info')
    return redirect(url_for('admin.manage_system_settings'))


@blueprint.route('/settings/reset-progress', methods=['POST'])
def reset_learning_progress():
    reset_scope = (request.form.get('reset_scope') or '').strip()
    confirmation = (request.form.get('confirmation') or '').strip()

    if reset_scope == 'user':
        user_id_raw = request.form.get('user_id')
        if not user_id_raw:
            flash('Vui lòng chọn người dùng.', 'warning')
            return redirect(url_for('admin.manage_system_settings'))

        try:
            user_id = int(user_id_raw)
        except (TypeError, ValueError):
            flash('ID người dùng không hợp lệ.', 'danger')
            return redirect(url_for('admin.manage_system_settings'))

        user = User.query.get(user_id)
        if not user:
            flash('Không tìm thấy người dùng.', 'danger')
            return redirect(url_for('admin.manage_system_settings'))

        expected_confirmation = f"RESET USER {user.username}"
        if confirmation != expected_confirmation:
            flash(f"Xác nhận sai. Cần nhập: '{expected_confirmation}'", 'warning')
            return redirect(url_for('admin.manage_system_settings'))

        # Reset logic
        UserContainerState.query.filter_by(user_id=user.user_id).delete(synchronize_session=False)
        LearningProgress.query.filter_by(user_id=user.user_id).delete(synchronize_session=False)
        Note.query.filter_by(user_id=user.user_id).delete(synchronize_session=False)
        UserFeedback.query.filter_by(user_id=user.user_id).delete(synchronize_session=False)
        ScoreLog.query.filter_by(user_id=user.user_id).delete(synchronize_session=False)

        user.total_score = 0
        db.session.commit()
        flash(f"Đã đặt lại tiến độ của {user.username}.", 'success')
        return redirect(url_for('admin.manage_system_settings'))

    if reset_scope == 'container':
        container_id_raw = request.form.get('container_id')
        if not container_id_raw:
            flash('Vui lòng chọn bộ câu hỏi.', 'warning')
            return redirect(url_for('admin.manage_system_settings'))

        try:
            container_id = int(container_id_raw)
        except (TypeError, ValueError):
            flash('ID không hợp lệ.', 'danger')
            return redirect(url_for('admin.manage_system_settings'))

        container = LearningContainer.query.get(container_id)
        if not container:
            flash('Không tìm thấy bộ câu hỏi.', 'danger')
            return redirect(url_for('admin.manage_system_settings'))

        expected_confirmation = f"RESET CONTAINER {container.container_id}"
        if confirmation != expected_confirmation:
            flash(f"Xác nhận sai. Cần nhập: '{expected_confirmation}'", 'warning')
            return redirect(url_for('admin.manage_system_settings'))

        item_subquery = db.session.query(LearningItem.item_id).filter(LearningItem.container_id == container.container_id).subquery()

        LearningProgress.query.filter(LearningProgress.item_id.in_(item_subquery)).delete(synchronize_session=False)
        Note.query.filter(
            (Note.reference_type == 'item') & Note.reference_id.in_(item_subquery) |
            (Note.reference_type == 'container') & (Note.reference_id == container.container_id)
        ).delete(synchronize_session=False)
        UserFeedback.query.filter(UserFeedback.item_id.in_(item_subquery)).delete(synchronize_session=False)
        ScoreLog.query.filter(ScoreLog.item_id.in_(item_subquery)).delete(synchronize_session=False)
        UserContainerState.query.filter_by(container_id=container.container_id).delete(synchronize_session=False)

        db.session.commit()
        flash(f"Đã đặt lại tiến độ cho bộ '{container.title}'.", 'success')
        return redirect(url_for('admin.manage_system_settings'))

    flash('Phạm vi không hợp lệ.', 'danger')
    return redirect(url_for('admin.manage_system_settings'))