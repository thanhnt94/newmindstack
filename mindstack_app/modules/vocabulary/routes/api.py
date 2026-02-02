from flask import request, jsonify, current_app, render_template_string
from flask_login import login_required, current_user
import traceback
import math

from . import blueprint
from mindstack_app.core.error_handlers import error_response
from mindstack_app.modules.vocabulary.services.vocabulary_service import VocabularyService
from mindstack_app.modules.stats.interface import StatsInterface as VocabularyContainerStats
from mindstack_app.modules.vocab_flashcard.interface import FlashcardInterface
from mindstack_app.modules.AI.interface import AIInterface
from mindstack_app.services.template_service import TemplateService

def _render_pagination(set_id, stats_data, page):
    """Render pagination HTML for AJAX response."""
    if not stats_data or 'pagination' not in stats_data:
        return ""
    
    p = stats_data['pagination']
    total_count = p.get('total', 0)
    per_page = p.get('per_page', 12)
    pages = int(math.ceil(total_count / float(per_page)))
    
    if pages <= 1:
        return ""

    # Simple pagination object for template
    class SimplePagination:
        def __init__(self, current_page, total_pages):
            self.page = current_page
            self.pages = total_pages
            self.has_prev = current_page > 1
            self.has_next = current_page < total_pages
            self.prev_num = current_page - 1
            self.next_num = current_page + 1

        def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
            last = 0
            for num in range(1, self.pages + 1):
                if num <= left_edge or \
                   (num > self.page - left_current - 1 and \
                    num < self.page + right_current) or \
                   num > self.pages - right_edge:
                    if last + 1 != num:
                        yield None
                    yield num
                    last = num

    pag_obj = SimplePagination(page, pages)
    version = TemplateService.get_active_version()
    try:
        # Use a string template to call the macro
        pagination_template_path = f"{version}/components/pagination/_pagination_mobile.html"
        base_url = f"/learn/vocabulary/api/set/{set_id}"
        tmpl = """
        {% from path import render_pagination_mobile with context %}
        {{ render_pagination_mobile(pagination, set_id=set_id, base_url=base_url) }}
        """
        return render_template_string(tmpl, pagination=pag_obj, set_id=set_id, path=pagination_template_path, base_url=base_url)
    except Exception as e:
        current_app.logger.error(f"Error rendering pagination: {e}")
        return f'<div class="flex justify-center p-4"><span class="text-sm text-slate-500">Trang {page} / {pages}</span></div>'

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
        return error_response(str(e), 'SERVER_ERROR', 500)

@blueprint.route('/api/flashcard-modes/<int:set_id>')
@login_required
def api_get_flashcard_modes(set_id):
    """API to get flashcard mode counts for inline rendering."""
    try:
        mode_data = FlashcardInterface.get_flashcard_mode_counts(current_user.user_id, set_id)
        modes = mode_data.get('list', [])
        
        # Filter to only essential modes for vocabulary learning
        essential_mode_ids = ['new_only', 'all_review', 'hard_only', 'mixed_srs', 'sequential']
        filtered_modes = [m for m in modes if m['id'] in essential_mode_ids]
        
        settings = VocabularyService.get_user_container_settings(current_user.user_id, set_id)
        user_button_count = settings.get('flashcard', {}).get('button_count', 4)

        return jsonify({
            'success': True,
            'modes': filtered_modes,
            'user_button_count': user_button_count,
            'settings': settings
        })
    except Exception as e:
        current_app.logger.error(f"Error getting flashcard modes API for set {set_id}: {e}")
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
        return error_response(str(e), 'SERVER_ERROR', 500)

@blueprint.route('/api/set/<int:set_id>')
@login_required
def api_get_set_detail(set_id):
    """API to get detailed info about a vocabulary set."""
    try:
        page = request.args.get('page', 1, type=int)
        sort_by = request.args.get('sort', 'default')
        result = VocabularyService.get_set_detail(current_user.user_id, set_id, page=page, sort_by=sort_by)
        
        pagination_html = _render_pagination(set_id, result.stats, page)
        
        set_data = result.set_info.__dict__.copy()
        if '_sa_instance_state' in set_data:
            del set_data['_sa_instance_state']
        set_data['can_edit'] = result.can_edit

        return jsonify({
            'success': True,
            'set': set_data,
            'course_stats': result.stats, # Alias for compatible JS
            'capabilities': result.capabilities,
            'can_edit': result.can_edit,
            'pagination_html': pagination_html
        })
    except Exception as e:
        current_app.logger.error(f"Error getting set detail API for set {set_id}: {e}")
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
        return error_response(str(e), 'SERVER_ERROR', 500)

@blueprint.route('/api/item/<int:item_id>/generate-ai', methods=['POST'])
@login_required
def api_generate_ai_explanation(item_id):
    """Generate AI explanation for a single item."""
    try:
        explanation = AIInterface.generate_item_explanation(item_id)
        return jsonify({'success': True, 'explanation': explanation})
    except Exception as e:
        current_app.logger.error(f"Error generating AI explanation for item {item_id}: {e}")
        return error_response(str(e), 'SERVER_ERROR', 500)
