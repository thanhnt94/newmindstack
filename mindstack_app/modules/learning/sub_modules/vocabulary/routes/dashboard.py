# File: vocabulary/routes/dashboard.py
# Vocabulary Hub - Dashboard and HTML Page Routes

from flask import render_template, request, abort, current_app
from flask_login import login_required, current_user

from . import vocabulary_bp
from mindstack_app.models import LearningContainer, User


@vocabulary_bp.route('/')
@vocabulary_bp.route('/dashboard')
@login_required
def dashboard():
    """Main vocabulary learning hub dashboard."""
    return render_template('v3/pages/learning/vocabulary/dashboard/index.html')


@vocabulary_bp.route('/set/<int:set_id>')
@login_required
def set_detail_page(set_id):
    """Vocabulary set detail page"""
    container = LearningContainer.query.get_or_404(set_id)
    can_edit_set = (current_user.user_role == User.ROLE_ADMIN or 
                    container.creator_user_id == current_user.user_id)
    
    return render_template('v3/pages/learning/vocabulary/dashboard/index.html', 
                          active_set_id=set_id, 
                          active_step='detail',
                          can_edit_set=can_edit_set,
                          set_id=set_id)


@vocabulary_bp.route('/set/<int:set_id>/modes')
@login_required
def set_modes_page(set_id):
    """Step 2: Learning modes selection page."""
    container = LearningContainer.query.get_or_404(set_id)
    
    # Get container capabilities
    ai_settings = container.ai_settings if hasattr(container, 'ai_settings') else {}
    capabilities = ai_settings.get('capabilities', []) if isinstance(ai_settings, dict) else []
    
    # Debug logging
    current_app.logger.info(f"[MODE FILTER] Container {set_id} ai_settings: {ai_settings}")
    current_app.logger.info(f"[MODE FILTER] Container {set_id} capabilities: {capabilities}")
    
    # Default to all modes if no capabilities set
    if not capabilities:
        current_app.logger.warning(f"[MODE FILTER] No capabilities set, defaulting to all modes")
        capabilities = ['supports_flashcard', 'supports_quiz', 'supports_writing', 'supports_listening', 'supports_speaking']
    
    return render_template('v3/pages/learning/vocabulary/dashboard/index.html', 
                          active_set_id=set_id, 
                          active_step='modes',
                          container_capabilities=capabilities)


@vocabulary_bp.route('/set/<int:set_id>/flashcard')
@login_required
def set_flashcard_page(set_id):
    """Step 3: Flashcard options page."""
    return render_template('v3/pages/learning/vocabulary/dashboard/index.html', active_set_id=set_id, active_step='flashcard-options')


@vocabulary_bp.route('/set/<int:set_id>/mcq')
@login_required
def set_mcq_page(set_id):
    """Step 3: MCQ options page."""
    return render_template('v3/pages/learning/vocabulary/dashboard/index.html', active_set_id=set_id, active_step='mcq-options')


@vocabulary_bp.route('/item/<int:item_id>/stats')
@login_required
def item_stats_page(item_id):
    """
    [NEW] Detailed statistics page for a single vocabulary item.
    """
    from ..stats.item_stats import VocabularyItemStats
    
    stats = VocabularyItemStats.get_item_stats(current_user.user_id, item_id)
    
    if not stats:
        abort(404, description="Item not found")

    if request.args.get('modal') == 'true':
        return render_template('v3/pages/learning/vocabulary/stats/_item_stats_content.html', stats=stats)
        
    return render_template('v3/pages/learning/vocabulary/stats/item_detail.html', stats=stats)
