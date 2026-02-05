from flask import render_template, request, flash, redirect, url_for
from mindstack_app.models import LearningContainer
from .. import blueprint
from ..models import GenerationLog
from ..interface import generate_bulk_from_container

@blueprint.route('/')
def index():
    """Chuyển hướng trực tiếp vào Factory Dashboard."""
    return redirect(url_for('content_generator.factory_dashboard'))

@blueprint.route('/factory', methods=['GET', 'POST'])
def factory_dashboard():
    """Giao diện chính để quản lý tạo nội dung hàng loạt."""
    if request.method == 'POST':
        container_id = request.form.get('container_id')
        options = {
            'batch_name': request.form.get('batch_name'),
            'gen_audio': 'gen_audio' in request.form,
            'gen_ai_content': 'gen_ai_content' in request.form,
            'overwrite': 'overwrite' in request.form,
            'voice_id': request.form.get('voice_id', 'default'),
            'delay_seconds': request.form.get('bulk_delay', 5, type=int)
        }
        try:
            result = generate_bulk_from_container(container_id, options, requester_module="admin_bulk")
            if result['tasks_created'] == 0:
                flash(f"No new content needed for '{result['container_title']}'. Everything is already up to date.", "info")
                return redirect(url_for('content_generator.factory_dashboard'))
                
            flash(f"Started session {result['session_id']} for {result['container_title']}. Queued {result['tasks_created']} tasks.", "success")
            return redirect(url_for('content_generator.factory_dashboard', active_session=result['session_id']))
        except Exception as e:
            flash(str(e), "danger")

    containers = LearningContainer.query.order_by(LearningContainer.title).all()
    return render_template('modules/content_generator/factory.html', containers=containers)