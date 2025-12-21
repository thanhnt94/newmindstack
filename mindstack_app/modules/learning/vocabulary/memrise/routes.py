from flask import render_template, request, jsonify, abort, Blueprint
from flask_login import login_required, current_user
from mindstack_app.models import LearningContainer
from .logic import generate_session_questions, process_answer, get_course_overview_stats
from mindstack_app.modules.shared.utils.db_session import safe_commit
from mindstack_app.models import db

# Define Blueprint here or import from __init__ (Assuming typical structure)
# For now, let's assume we import the Blueprint object from . which we must create
from . import memrise_bp

@memrise_bp.route('/course/<int:container_id>')
@login_required
def course_overview(container_id):
    """Memrise Course Overview Page."""
    container = LearningContainer.query.get_or_404(container_id)
    page = request.args.get('page', 1, type=int)
    
    stats = get_course_overview_stats(current_user.user_id, container_id, page=page)
    
    return render_template('memrise/course/overview.html', container=container, stats=stats)

@memrise_bp.route('/session/<int:container_id>')
@login_required
def session(container_id):
    """Memrise Session Page."""
    container = LearningContainer.query.get_or_404(container_id)
    return render_template('memrise/session/index.html', container=container)

@memrise_bp.route('/api/questions/<int:container_id>')
@login_required
def api_get_questions(container_id):
    limit = request.args.get('count', 10, type=int)
    questions = generate_session_questions(current_user.user_id, container_id, limit)
    return jsonify({
        'success': True,
        'questions': questions
    })

@memrise_bp.route('/api/check', methods=['POST'])
@login_required
def api_check():
    data = request.get_json()
    item_id = data.get('item_id')
    q_type = data.get('type')
    answer = data.get('answer')
    
    result = process_answer(current_user.user_id, item_id, q_type, answer)
    safe_commit(db.session)
    
    return jsonify({
        'success': True,
        'result': result
    })
