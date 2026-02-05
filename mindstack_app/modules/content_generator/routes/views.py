from flask import render_template, request, current_app, flash, redirect, url_for
from .. import blueprint
from ..models import GenerationLog
from ..interface import generate_text, generate_audio

@blueprint.route('/')
def index():
    """Admin Dashboard for Content Generator."""
    page = request.args.get('page', 1, type=int)
    logs = GenerationLog.query.order_by(GenerationLog.created_at.desc()).paginate(page=page, per_page=20)
    # Path is now relative to the theme's template folder
    return render_template('modules/content_generator/index.html', logs=logs)

@blueprint.route('/test', methods=['GET', 'POST'])
def test_generator():
    """Manual testing interface."""
    if request.method == 'POST':
        gen_type = request.form.get('type')
        prompt = request.form.get('prompt')
        session_id = request.form.get('session_id') or "manual_test"
        delay = request.form.get('delay', 0, type=int)
        
        try:
            if gen_type == 'text':
                generate_text(prompt, requester_module="admin_test", session_id=session_id, delay_seconds=delay)
                flash(f"Text generation task queued (Delay: {delay}s)!", "success")
            elif gen_type == 'audio':
                generate_audio(prompt, voice_id="default", requester_module="admin_test", session_id=session_id, delay_seconds=delay)
                flash(f"Audio generation task queued (Delay: {delay}s)!", "success")
            elif gen_type == 'image':
                 generate_image(prompt, requester_module="admin_test", session_id=session_id, delay_seconds=delay)
                 flash(f"Image generation task queued (Delay: {delay}s)!", "success")
            
            return redirect(url_for('content_generator.index'))
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
            
    return render_template('modules/content_generator/test.html')
