from flask import render_template, request, abort, current_app, redirect, url_for
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
from . import blueprint
from ..services.vocabulary_service import VocabularyService
from mindstack_app.modules.learning.interface import LearningInterface

@blueprint.route('/')
@blueprint.route('/dashboard')
@login_required
def dashboard():
    """Main vocabulary learning hub dashboard."""
    score_data = LearningInterface.get_score_breakdown(current_user.user_id)
    weekly_active_days = LearningInterface.get_weekly_active_days_count(current_user.user_id)
    score_overview = {
        'today': score_data['today'],
        'week': score_data['week'],
        'total': score_data['total'],
        'active_days': weekly_active_days
    }
    return render_dynamic_template('modules/vocabulary/dashboard/index.html', score_overview=score_overview)

@blueprint.route('/set/<int:set_id>')
@login_required
def set_detail_page(set_id):
    """Vocabulary set detail page"""
    detail = VocabularyService.get_set_detail(current_user.user_id, set_id)
    
    score_data = LearningInterface.get_score_breakdown(current_user.user_id)
    weekly_active_days = LearningInterface.get_weekly_active_days_count(current_user.user_id)
    score_overview = {
        'today': score_data['today'],
        'week': score_data['week'],
        'total': score_data['total'],
        'active_days': weekly_active_days
    }
    
    return render_dynamic_template('modules/vocabulary/dashboard/detail.html', 
                          active_set_id=set_id, 
                          can_edit_set=detail.can_edit,
                          set_id=set_id,
                          score_overview=score_overview,
                          set_info=detail.set_info,
                          stats=detail.stats)

@blueprint.route('/modes/redirect/<int:set_id>')
@login_required
def set_modes_redirect(set_id):
    """Legacy redirect support."""
    return redirect(url_for('vocabulary.modes_selection_page', set_id=set_id))

@blueprint.route('/modes/<int:set_id>')
@login_required
def modes_selection_page(set_id):
    """
    Dedicated Modes Selection Page (Wizard Style).
    New URL: /learn/vocabulary/modes/<set_id>
    """
    detail = VocabularyService.get_set_detail(current_user.user_id, set_id)
    return render_dynamic_template('modules/vocabulary/modes/index.html', 
                                  container=detail.set_info,
                                  capabilities=detail.capabilities)

@blueprint.route('/set/<int:set_id>/flashcard')
@login_required
def set_flashcard_page(set_id):
    """Step 3: Flashcard options page - Redirect."""
    return redirect(url_for('vocab_flashcard.setup', sets=set_id))

@blueprint.route('/set/<int:set_id>/mcq')
@login_required
def set_mcq_page(set_id):
    """Step 3: MCQ options page - Redirect."""
    return redirect(url_for('vocab_mcq.mcq_setup', set_id=set_id))

@blueprint.route('/item/<int:item_id>/stats')
@login_required
def item_stats_page(item_id):
    """Detailed statistics page for a single vocabulary item."""
    stats = VocabularyService.get_item_stats(current_user.user_id, item_id)
    
    if not stats:
        abort(404, description="Item not found")

    if request.args.get('modal') == 'true':
        return render_dynamic_template('modules/vocabulary/detail/_vocab_detail_content.html', stats=stats)
        
    return render_dynamic_template('modules/vocabulary/detail/vocab_detail.html', stats=stats)

