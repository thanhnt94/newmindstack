# File: vocabulary/routes/dashboard.py
# Vocabulary Hub - Dashboard and HTML Page Routes

from flask import render_template, request, abort, current_app, redirect, url_for
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user

from . import blueprint
from mindstack_app.models import LearningContainer, User


@blueprint.route('/')
@blueprint.route('/dashboard')
@login_required
def dashboard():
    """Main vocabulary learning hub dashboard."""
    from mindstack_app.modules.learning.services.learning_metrics_service import LearningMetricsService
    score_data = LearningMetricsService.get_score_breakdown(current_user.user_id)
    weekly_active_days = LearningMetricsService.get_weekly_active_days_count(current_user.user_id)
    score_overview = {
        'today': score_data['today'],
        'week': score_data['week'],
        'total': score_data['total'],
        'active_days': weekly_active_days
    }
    return render_dynamic_template('modules/learning/vocabulary/dashboard/index.html', score_overview=score_overview)


@blueprint.route('/set/<int:set_id>')
@login_required
def set_detail_page(set_id):
    """Vocabulary set detail page"""
    container = LearningContainer.query.get_or_404(set_id)
    can_edit_set = (current_user.user_role == User.ROLE_ADMIN or 
                    container.creator_user_id == current_user.user_id)
    
    from mindstack_app.modules.learning.services.learning_metrics_service import LearningMetricsService
    score_data = LearningMetricsService.get_score_breakdown(current_user.user_id)
    weekly_active_days = LearningMetricsService.get_weekly_active_days_count(current_user.user_id)
    score_overview = {
        'today': score_data['today'],
        'week': score_data['week'],
        'total': score_data['total'],
        'active_days': weekly_active_days
    }
    
    return render_dynamic_template('modules/learning/vocabulary/dashboard/detail.html', 
                          active_set_id=set_id, 
                          can_edit_set=can_edit_set,
                          set_id=set_id,
                          score_overview=score_overview)


@blueprint.route('/set/<int:set_id>/modes')
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
    
    return redirect(url_for('vocabulary.modes_selection_page', set_id=set_id))


@blueprint.route('/modes/<int:set_id>')
@login_required
def modes_selection_page(set_id):
    """
    [NEW] Dedicated Modes Selection Page (Wizard Style).
    New URL: /learn/vocabulary/modes/<set_id>
    """
    container = LearningContainer.query.get_or_404(set_id)
    return render_dynamic_template('modules/learning/vocabulary/modes/index.html', container=container)


@blueprint.route('/set/<int:set_id>/flashcard')
@login_required
def set_flashcard_page(set_id):
    """Step 3: Flashcard options page."""
    return redirect(url_for('vocab_flashcard.flashcard_learning.setup', set_id=set_id))


@blueprint.route('/set/<int:set_id>/mcq')
@login_required
def set_mcq_page(set_id):
    """Step 3: MCQ options page - Redirect to new setup wizard."""
    return redirect(url_for('vocab_mcq.mcq_setup', set_id=set_id))


@blueprint.route('/item/<int:item_id>/stats')
@login_required
def item_stats_page(item_id):
    """
    [NEW] Detailed statistics page for a single vocabulary item.
    """
    from ..services.stats_item import VocabularyItemStats
    
    stats = VocabularyItemStats.get_item_stats(current_user.user_id, item_id)
    
    if not stats:
        abort(404, description="Item not found")

    if request.args.get('modal') == 'true':
        return render_dynamic_template('modules/learning/vocabulary/stats/_item_stats_content.html', stats=stats)
        
    return render_dynamic_template('modules/learning/vocabulary/stats/item_detail.html', stats=stats)


@blueprint.route('/assets/<path:filename>')
def serve_dashboard_asset(filename):
    """Serve static assets from the dashboard template directory."""
    import os
    from flask import send_from_directory
    from mindstack_app.services.template_service import TemplateService
    
    # Resolve directory dynamically based on active template version
    version = TemplateService.get_active_version()
    directory = os.path.join(
        current_app.root_path, 
        'themes', 
        version,
        'templates',
        version, 
        'modules', 'learning', 'vocabulary', 'dashboard'
    )
    return send_from_directory(directory, filename)
