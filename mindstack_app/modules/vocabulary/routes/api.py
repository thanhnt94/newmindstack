# File: vocabulary/routes/api.py
# Vocabulary Hub - API Endpoints

from flask import request, jsonify, render_template_string, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_
import math

from . import vocabulary_bp
from mindstack_app.core.error_handlers import error_response, success_response
from mindstack_app.models import (
    LearningContainer, LearningItem, User, UserContainerState, db, LearningProgress
)

# Import flashcard engine for session management
from ...flashcard.engine import get_flashcard_mode_counts
from mindstack_app.modules.AI.services.ai_manager import get_ai_service
from mindstack_app.modules.AI.logics.prompts import get_formatted_prompt


# Helper for manual pagination object mocking SQLAlchemy pagination
class SimplePagination:
    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total = total_count
        self.pages = int(math.ceil(total_count / float(per_page)))
        self.has_prev = page > 1
        self.has_next = page < self.pages
        self.prev_num = page - 1
        self.next_num = page + 1

    def iter_pages(self, left_edge=0, right_edge=0, left_current=1, right_current=1):
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.pages - right_edge) or \
               (num >= self.page - left_current and num <= self.page + right_current):
                if last + 1 != num:
                    yield None
                yield num
                last = num


@vocabulary_bp.route('/api/dashboard-global-stats')
@login_required
def api_get_dashboard_stats():
    """API to get global vocabulary dashboard statistics."""
    from ..stats.container_stats import VocabularyContainerStats
    try:
        stats = VocabularyContainerStats.get_global_stats(current_user.user_id)
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        current_app.logger.error(f"Error getting dashboard stats: {e}")
        return error_response(str(e), 'SERVER_ERROR', 500)


@vocabulary_bp.route('/api/sets')
@login_required  
def api_get_sets():
    """API to get vocabulary sets with search and category filter."""
    search = request.args.get('q', '').strip()
    category = request.args.get('category', 'my')  # my, learning, explore
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # Base query - only flashcard sets
    query = LearningContainer.query.filter(
        LearningContainer.container_type == 'FLASHCARD_SET'
    )
    
    # Category filter
    if category == 'my':
        # Sets created by user
        query = query.filter(LearningContainer.creator_user_id == current_user.user_id)
    elif category == 'learning':
        # Sets user is currently learning (has UserContainerState)
        learning_ids = [
            ucs.container_id for ucs in 
            UserContainerState.query.filter_by(
                user_id=current_user.user_id,
                is_archived=False
            ).all()
        ]
        query = query.filter(LearningContainer.container_id.in_(learning_ids))
    elif category == 'explore':
        # All public sets (including user's own)
        query = query.filter(
            LearningContainer.is_public == True
        )
    
    # Search filter
    if search:
        query = query.filter(
            or_(
                LearningContainer.title.ilike(f'%{search}%'),
                LearningContainer.description.ilike(f'%{search}%')
            )
        )
    
    # Order by last accessed or created
    query = query.order_by(LearningContainer.created_at.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    
    # Build response
    sets = []
    for c in pagination.items:
        # Count flashcard items
        card_count = LearningItem.query.filter_by(
            container_id=c.container_id,
            item_type='FLASHCARD'
        ).count()
        
        # Get creator info
        creator = User.query.get(c.creator_user_id)
        
        sets.append({
            'id': c.container_id,
            'title': c.title,
            'description': c.description or '',
            'cover_image': c.cover_image,
            'card_count': card_count,
            'creator_name': creator.username if creator else 'Unknown',
            'creator_avatar': None,  # User model doesn't have avatar_url
            'is_public': c.is_public,
        })
    
    return jsonify({
        'success': True,
        'sets': sets,
        'has_next': pagination.has_next,
        'has_prev': pagination.has_prev,
        'page': page,
        'total': pagination.total
    })


@vocabulary_bp.route('/api/flashcard-modes/<int:set_id>')
@login_required
def api_get_flashcard_modes(set_id):
    """API to get flashcard mode counts for inline rendering."""
    try:
        modes = get_flashcard_mode_counts(current_user.user_id, set_id)
        
        # Filter to only essential modes for vocabulary learning
        essential_mode_ids = ['new_only', 'all_review', 'hard_only', 'mixed_srs']
        filtered_modes = [m for m in modes if m['id'] in essential_mode_ids]
        
        # [NEW] Get user per-set preferences
        user_button_count = 4 # Default
        uc_state = None
        try:
            uc_state = UserContainerState.query.filter_by(
                user_id=current_user.user_id, 
                container_id=set_id
            ).first()
            if uc_state and uc_state.settings:
                # Safely access nested dict
                flashcard_settings = uc_state.settings.get('flashcard', {})
                if 'button_count' in flashcard_settings:
                    user_button_count = flashcard_settings['button_count']
        except Exception as e:
            pass # Fail silently to default

        return jsonify({
            'success': True,
            'modes': filtered_modes,
            'user_button_count': user_button_count,
            'settings': uc_state.settings if (uc_state and uc_state.settings) else {}
        })
    except Exception as e:
        return error_response(str(e), 'SERVER_ERROR', 500)


@vocabulary_bp.route('/api/settings/container/<int:set_id>', methods=['POST', 'DELETE'])
@login_required
def api_container_settings(set_id):
    """
    API to manage per-container user settings.
    POST: Update settings (merge).
    DELETE: Reset settings to default.
    """
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


@vocabulary_bp.route('/api/set/<int:set_id>')
@login_required
def api_get_set_detail(set_id):
    """API to get detailed info about a vocabulary set."""
    container = LearningContainer.query.get_or_404(set_id)
    
    # Count flashcard items
    card_count = LearningItem.query.filter_by(
        container_id=container.container_id,
        item_type='FLASHCARD'
    ).count()
    
    # Count memrise-eligible items
    memrise_count = 0
    items = LearningItem.query.filter_by(
        container_id=container.container_id,
        item_type='FLASHCARD'
    ).all()
    for item in items:
        content = item.content or {}
        if content.get('memrise_prompt') and content.get('memrise_answers'):
            memrise_count += 1
    
    # Get creator
    creator = User.query.get(container.creator_user_id)
    
    # Get SRS Stats for Course Overview
    course_stats = None
    page = request.args.get('page', 1, type=int)
    pagination_html = ""

    try:
        from ..logics.stats_logic import get_course_overview_stats
        course_stats = get_course_overview_stats(current_user.user_id, set_id, page=page, per_page=12)
        
        # DEBUG: Write stats info to file
        with open('debug_api_stats.txt', 'w', encoding='utf-8') as f:
            if course_stats:
                f.write(f"Success! Items count: {len(course_stats.get('items', []))}\n")
                f.write(f"Pagination: {course_stats.get('pagination')}\n")
            else:
                f.write("Success but course_stats is None (Why?)\n")

        if course_stats and 'pagination' in course_stats:
             p = course_stats['pagination']
             # Create dummy pagination object - Force page from request to be sure
             pag_obj = SimplePagination(int(page), 12, int(p['total']))
             
             # Get active version
             from mindstack_app.services.template_service import TemplateService
             version = TemplateService.get_active_version()
             
             # Render template
             tmpl = """
             {% from version ~ '/includes/pagination/_pagination_mobile.html' import render_pagination_mobile %}
             {{ render_pagination_mobile(pagination, set_id=set_id) }}
             """
             pagination_html = render_template_string(tmpl, pagination=pag_obj, set_id=set_id, version=version)

    except Exception as e:
        import traceback
        err_msg = f"ERROR calculating course stats for set {set_id}: {e}\n{traceback.format_exc()}"
        current_app.logger.error(err_msg)
        
        # DEBUG: Write error to file
        with open('debug_api_error.txt', 'w', encoding='utf-8') as f:
            f.write(err_msg)
            
        # Return error info to client for debugging
        course_stats = {'error': str(e), 'trace': traceback.format_exc(), 'items': []}

    return jsonify({
        'success': True,
        'set': {
            'id': container.container_id,
            'title': container.title,
            'description': container.description or '',
            'cover_image': container.cover_image,
            'card_count': card_count,
            'memrise_count': memrise_count,
            'creator_name': creator.username if creator else 'Unknown',
            'creator_avatar': None,
            'is_public': container.is_public,
            'capabilities': list(container.capability_flags()),
            'can_edit': (current_user.user_role == User.ROLE_ADMIN or container.creator_user_id == current_user.user_id),
        },
        'course_stats': course_stats,
        'pagination_html': pagination_html
    })


@vocabulary_bp.route('/api/stats/container/<int:container_id>')
@login_required
def api_get_container_stats(container_id):
    """
    API endpoint for comprehensive container statistics.
    Used by the container stats modal on the vocabulary dashboard.
    """
    from ..stats.container_stats import VocabularyContainerStats
    
    try:
        # Get basic stats
        stats = VocabularyContainerStats.get_full_stats(current_user.user_id, container_id)
        
        # Get chart data
        chart_data = VocabularyContainerStats.get_chart_data(current_user.user_id, container_id)
        
        # Calculate average memory power (mastery avg as percentage)
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
        import traceback
        current_app.logger.error(f"Error getting container stats: {e}\n{traceback.format_exc()}")
        return error_response(str(e), 'SERVER_ERROR', 500)


@vocabulary_bp.route('/api/progress/<int:item_id>/note', methods=['POST'])
@login_required
def api_save_item_note(item_id):
    """
    Save or update user note for a specific item.
    Notes are stored in LearningProgress.mode_data['note'].
    """
    payload = request.get_json() or {}
    note_content = payload.get('note', '').strip()
    
    try:
        # Get progress record
        progress = LearningProgress.query.filter_by(
            user_id=current_user.user_id,
            item_id=item_id,
            learning_mode=LearningProgress.MODE_FLASHCARD
        ).first()
        
        if not progress:
            # Create if not exists (unlikely but possible)
            progress = LearningProgress(
                user_id=current_user.user_id,
                item_id=item_id,
                learning_mode=LearningProgress.MODE_FLASHCARD,
                status='new'
            )
            db.session.add(progress)
            
        # Update mode_data safely
        mode_data = dict(progress.mode_data) if progress.mode_data else {}
        mode_data['note'] = note_content
        progress.mode_data = mode_data
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Ghi chú đã được lưu.'})
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving note for item {item_id}: {e}")
        return error_response(str(e), 'SERVER_ERROR', 500)

@vocabulary_bp.route('/api/item/<int:item_id>/generate-ai', methods=['POST'])
@login_required
def api_generate_ai_explanation(item_id):
    """Generate AI explanation for a single item."""
    item = LearningItem.query.get_or_404(item_id)
    
    try:
        current_app.logger.info(f"Generating AI explanation for item {item_id}")
        ai_client = get_ai_service()
        if not ai_client:
            return jsonify({'success': False, 'message': 'Chưa cấu hình dịch vụ AI.'}), 503
            
        prompt = get_formatted_prompt(item, purpose="explanation")
        if not prompt:
            return jsonify({'success': False, 'message': 'Không thể tạo prompt cho học liệu này.'}), 400
            
        item_info = f"{item.item_type} ID {item.item_id}"
        success, ai_response = ai_client.generate_content(prompt, item_info)
        
        if not success:
            current_app.logger.error(f"AI Service error for item {item_id}: {ai_response}")
            return jsonify({'success': False, 'message': f'Lỗi từ AI: {ai_response}'}), 500
            
        item.ai_explanation = ai_response
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Đã tạo nội dung AI thành công.', 'explanation': ai_response})
        
    except Exception as e:
        db.session.rollback()
        import traceback
        error_details = traceback.format_exc()
        current_app.logger.error(f"Error generating AI for item {item_id}: {e}\n{error_details}")
        return error_response(str(e), 'SERVER_ERROR', 500, details={'trace': error_details})
