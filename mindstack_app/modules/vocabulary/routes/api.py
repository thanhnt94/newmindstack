# File: vocabulary/routes/api.py
# Vocabulary Hub - API Endpoints

from flask import request, jsonify, current_app
from flask_login import login_required, current_user
import traceback

from .. import vocabulary_bp as blueprint
from mindstack_app.core.error_handlers import error_response
from mindstack_app.models import (
    LearningContainer, LearningItem, UserContainerState, db
)

# Import Services
from ..services.vocabulary_service import VocabularyService
# VocabularyContainerStats was removed, logic moved to stats module
from mindstack_app.modules.stats.interface import StatsInterface as VocabularyContainerStats
from ...vocab_flashcard.engine.algorithms import get_flashcard_mode_counts
from mindstack_app.modules.AI.interface import generate_content
from mindstack_app.modules.AI.logics.prompts import get_formatted_prompt

@blueprint.route('/api/dashboard-global-stats')
@login_required
def api_get_dashboard_stats():
    """API to get global vocabulary dashboard statistics."""
    try:
        stats = VocabularyContainerStats.get_global_stats(current_user.user_id)
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        current_app.logger.error(f"Error getting dashboard stats: {e}")
        current_app.logger.error(traceback.format_exc())
        return error_response(str(e), 'SERVER_ERROR', 500)

@blueprint.route('/api/sets')
@login_required  
def api_get_sets():
    """API to get vocabulary sets with search and category filter."""
    search = request.args.get('q', '').strip()
    category = request.args.get('category', 'my')
    page = request.args.get('page', 1, type=int)
    
    try:
        result = VocabularyService.get_vocabulary_sets(
            user_id=current_user.user_id,
            category=category,
            search=search,
            page=page
        )
        return jsonify({
            'success': True,
            **result
        })
    except Exception as e:
        current_app.logger.error(f"Error getting sets API: {e}")
        current_app.logger.error(traceback.format_exc())
        return error_response(str(e), 'SERVER_ERROR', 500)

@blueprint.route('/api/flashcard-modes/<int:set_id>')
@login_required
def api_get_flashcard_modes(set_id):
    """API to get flashcard mode counts for inline rendering."""
    try:
        modes = get_flashcard_mode_counts(current_user.user_id, set_id)
        
        # Filter to only essential modes for vocabulary learning
        essential_mode_ids = ['new_only', 'all_review', 'hard_only', 'mixed_srs', 'sequential']
        filtered_modes = [m for m in modes if m['id'] in essential_mode_ids]
        
        # [NEW] Get user per-set preferences
        user_button_count = 4 # Default
        uc_state = UserContainerState.query.filter_by(
            user_id=current_user.user_id, 
            container_id=set_id
        ).first()
        
        settings = {}
        if uc_state and uc_state.settings:
            settings = uc_state.settings
            flashcard_settings = settings.get('flashcard', {})
            user_button_count = flashcard_settings.get('button_count', 4)

        return jsonify({
            'success': True,
            'modes': filtered_modes,
            'user_button_count': user_button_count,
            'settings': settings
        })
    except Exception as e:
        current_app.logger.error(f"Error getting flashcard modes API for set {set_id}: {e}")
        current_app.logger.error(traceback.format_exc())
        return error_response(str(e), 'SERVER_ERROR', 500)

@blueprint.route('/api/settings/container/<int:set_id>', methods=['POST', 'DELETE'])
@login_required
def api_container_settings(set_id):
    """API to manage per-container user settings."""
    from mindstack_app.modules.learning.services.settings_service import LearningSettingsService
    try:
        if request.method == 'DELETE':
            LearningSettingsService.update_container_settings(current_user.user_id, set_id, {
                'flashcard': {}, 'quiz': {}, 'listening': {}, 'typing': {}
            })
            return jsonify({'success': True, 'message': 'Cài đặt đã được reset.'})

        payload = request.get_json() or {}
        new_settings = LearningSettingsService.update_container_settings(current_user.user_id, set_id, payload)
        return jsonify({'success': True, 'settings': new_settings})
    except Exception as e:
        current_app.logger.error(f"Error managing settings for set {set_id}: {e}")
        current_app.logger.error(traceback.format_exc())
        return error_response(str(e), 'SERVER_ERROR', 500)

@blueprint.route('/api/set/<int:set_id>')
@login_required
def api_get_set_detail(set_id):
    """API to get detailed info about a vocabulary set."""
    try:
        page = request.args.get('page', 1, type=int)
        result = VocabularyService.get_set_detail(current_user.user_id, set_id, page=page)
        return jsonify({
            'success': True,
            **result
        })
    except Exception as e:
        current_app.logger.error(f"Error getting set detail API for set {set_id}: {e}")
        current_app.logger.error(traceback.format_exc())
        return error_response(str(e), 'SERVER_ERROR', 500)

@blueprint.route('/api/stats/container/<int:container_id>')
@login_required
def api_get_container_stats(container_id):
    """API endpoint for comprehensive container statistics."""
    try:
        stats = VocabularyContainerStats.get_full_stats(current_user.user_id, container_id)
        chart_data = VocabularyContainerStats.get_chart_data(current_user.user_id, container_id)
        average_memory_power = round(stats['mastery_avg'] * 100, 1) if stats['mastery_avg'] else 0
        
        return jsonify({
            'success': True,
            'average_memory_power': average_memory_power,
            'total_items': stats['total'],
            'due_items': stats['due'],
            'learned_items': stats['learned'],
            'mastered_items': stats['mastered'],
            'chart_data': chart_data
        })
    except Exception as e:
        current_app.logger.error(f"Error getting container stats: {e}")
        current_app.logger.error(traceback.format_exc())
        return error_response(str(e), 'SERVER_ERROR', 500)

@blueprint.route('/api/progress/<int:item_id>/note', methods=['POST'])
@login_required
def api_save_item_note(item_id):
    """Save or update user note for a specific item."""
    payload = request.get_json() or {}
    note_content = payload.get('note', '').strip()
    
    try:
        VocabularyService.save_item_note(current_user.user_id, item_id, note_content)
        return jsonify({'success': True, 'message': 'Ghi chú đã được lưu.'})
    except Exception as e:
        current_app.logger.error(f"Error saving note for item {item_id}: {e}")
        current_app.logger.error(traceback.format_exc())
        return error_response(str(e), 'SERVER_ERROR', 500)

@blueprint.route('/api/item/<int:item_id>/generate-ai', methods=['POST'])
@login_required
def api_generate_ai_explanation(item_id):
    """Generate AI explanation for a single item."""
    item = LearningItem.query.get_or_404(item_id)
    
    try:
        prompt = get_formatted_prompt(item, purpose="explanation")
        if not prompt:
            return jsonify({'success': False, 'message': 'Không thể tạo prompt.'}), 400
            
        response = generate_content(prompt, feature="explanation", context_ref=f"ITEM_{item_id}")
        
        if not response.success:
            return jsonify({'success': False, 'message': f'AI Error: {response.error}'}), 500
            
        item.ai_explanation = response.content
        db.session.commit()
        return jsonify({'success': True, 'explanation': response.content})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error generating AI explanation for item {item_id}: {e}")
        current_app.logger.error(traceback.format_exc())
        return error_response(str(e), 'SERVER_ERROR', 500)
