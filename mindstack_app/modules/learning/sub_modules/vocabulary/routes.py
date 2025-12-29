# File: mindstack_app/modules/learning/vocabulary/routes.py
# Vocabulary Learning Hub Routes
# Updated to use flashcard engine for session management

from flask import render_template, request, jsonify, redirect, url_for, flash, abort, current_app, session
from flask_login import login_required, current_user
from sqlalchemy import or_

from . import vocabulary_bp
from mindstack_app.models import (
    LearningContainer, LearningItem, User, UserContainerState, db
)
from mindstack_app.modules.shared.utils.db_session import safe_commit

# Import flashcard engine for session management
from ..flashcard.engine import (
    FlashcardSessionManager,
    FlashcardLearningConfig,
    get_flashcard_mode_counts,
)


@vocabulary_bp.route('/')
@vocabulary_bp.route('/dashboard')
@login_required
def dashboard():
    """Main vocabulary learning hub dashboard."""
    return render_template('vocabulary/dashboard/default/index.html')


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
        # Public sets not created by user
        query = query.filter(
            LearningContainer.is_public == True,
            LearningContainer.creator_user_id != current_user.user_id
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


@vocabulary_bp.route('/set/<int:set_id>')
@login_required
def set_detail_page(set_id):
    """Vocabulary set detail page"""
    # Check if user can edit this set
    from mindstack_app.models import LearningContainer, User
    container = LearningContainer.query.get_or_404(set_id)
    can_edit_set = (current_user.user_role == User.ROLE_ADMIN or 
                    container.creator_user_id == current_user.user_id)
    
    return render_template('vocabulary/dashboard/default/index.html', 
                          active_set_id=set_id, 
                          active_step='detail',
                          can_edit_set=can_edit_set,
                          set_id=set_id)


@vocabulary_bp.route('/set/<int:set_id>/modes')
@login_required
def set_modes_page(set_id):
    """Step 2: Learning modes selection page."""
    from mindstack_app.models import LearningContainer
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
    
    return render_template('vocabulary/dashboard/default/index.html', 
                          active_set_id=set_id, 
                          active_step='modes',
                          container_capabilities=capabilities)


@vocabulary_bp.route('/set/<int:set_id>/flashcard')
@login_required
def set_flashcard_page(set_id):
    """Step 3: Flashcard options page."""
    return render_template('vocabulary/dashboard/default/index.html', active_set_id=set_id, active_step='flashcard-options')


@vocabulary_bp.route('/set/<int:set_id>/mcq')
@login_required
def set_mcq_page(set_id):
    """Step 3: MCQ options page."""
    return render_template('vocabulary/dashboard/default/index.html', active_set_id=set_id, active_step='mcq-options')


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
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


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
        return jsonify({'success': False, 'message': str(e)}), 500




# Helper for manual pagination object mocking SQLAlchemy pagination
class SimplePagination:
    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total = total_count
        import math
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
    from flask import render_template_string
    pagination_html = ""

    try:
        from .memrise.logic import get_course_overview_stats
        course_stats = get_course_overview_stats(current_user.user_id, set_id, page=page, per_page=12)
        
        if course_stats and 'pagination' in course_stats:
             p = course_stats['pagination']
             p = course_stats['pagination']
             # Create dummy pagination object - Force page from request to be sure
             pag_obj = SimplePagination(int(page), 12, int(p['total']))
             
             # Render template
             tmpl = """
             {% from 'includes/_pagination_mobile.html' import render_pagination_mobile %}
             {{ render_pagination_mobile(pagination, set_id=set_id) }}
             """
             pagination_html = render_template_string(tmpl, pagination=pag_obj, set_id=set_id)

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR calculating course stats for set {set_id}: {e}")
        return jsonify({
            'success': False, 
            'message': f"Error calculating stats: {str(e)}"
        })

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


# ============================================
# Flashcard Session Routes (using engine)
# ============================================

@vocabulary_bp.route('/flashcard/start/<int:set_id>/<string:mode>')
@login_required
def start_flashcard_session(set_id, mode):
    """Bắt đầu phiên học flashcard cho một bộ từ vựng."""
    
    # Pre-fetch user container state
    uc_state = UserContainerState.query.filter_by(
        user_id=current_user.user_id,
        container_id=set_id
    ).first()
    
    # [NEW] Load parameters from URL (or use session defaults)
    rating_levels = request.args.get('rating_levels', type=int)
    url_autoplay = request.args.get('autoplay') == 'true' if 'autoplay' in request.args else None
    url_show_image = request.args.get('show_image') == 'true' if 'show_image' in request.args else None
    url_show_stats = request.args.get('show_stats') == 'true' if 'show_stats' in request.args else None

    # Sync with Session Overrides
    if rating_levels and rating_levels in [3, 4, 6]:
        session['flashcard_button_count_override'] = rating_levels
        
    # [ACTION] Persist changes if Auto-Save is ON
    try:
        if not uc_state:
             uc_state = UserContainerState(
                user_id=current_user.user_id, 
                container_id=set_id,
                is_archived=False,
                is_favorite=False,
                settings={}
            )
             db.session.add(uc_state)
        
        # Determine if we should auto-save
        new_settings = dict(uc_state.settings or {})
        should_auto_save = new_settings.get('auto_save', True)
        
        if 'flashcard' not in new_settings: 
            new_settings['flashcard'] = {}
        
        changed = False

        # 1. Handle Button Count Auto-Save
        if should_auto_save and rating_levels:
            if new_settings['flashcard'].get('button_count') != rating_levels:
                new_settings['flashcard']['button_count'] = rating_levels
                changed = True
        
        # 2. Handle Visual Settings Auto-Save (if passed in URL, e.g. from a quick toggle)
        if should_auto_save:
            if url_autoplay is not None and new_settings['flashcard'].get('autoplay') != url_autoplay:
                new_settings['flashcard']['autoplay'] = url_autoplay
                changed = True
            if url_show_image is not None and new_settings['flashcard'].get('show_image') != url_show_image:
                new_settings['flashcard']['show_image'] = url_show_image
                changed = True
            if url_show_stats is not None and new_settings['flashcard'].get('show_stats') != url_show_stats:
                new_settings['flashcard']['show_stats'] = url_show_stats
                changed = True
        
        if changed:
            uc_state.settings = new_settings
            db.session.add(uc_state)
            safe_commit(db.session)
            
    except Exception as e:
        current_app.logger.warning(f"Failed to persist flashcard settings: {e}")
            
    # [FINALIZE] Load final configuration to Session
    try:
        flashcard_settings = uc_state.settings.get('flashcard', {}) if uc_state and uc_state.settings else {}
        
        # Priority: URL Override > Persisted Setting > Default 4
        final_button_count = rating_levels or flashcard_settings.get('button_count') or 4
        session['flashcard_button_count_override'] = final_button_count
        
        # Visual settings
        global_prefs = current_user.last_preferences or {}
        visual_settings = {
            'autoplay': flashcard_settings.get('autoplay', global_prefs.get('flashcard_autoplay_audio', False)),
            'show_image': flashcard_settings.get('show_image', global_prefs.get('flashcard_show_image', True)),
            'show_stats': flashcard_settings.get('show_stats', global_prefs.get('flashcard_show_stats', True))
        }
        
        # Override with URL params if present (even if not auto-saving)
        if url_autoplay is not None: visual_settings['autoplay'] = url_autoplay
        if url_show_image is not None: visual_settings['show_image'] = url_show_image
        if url_show_stats is not None: visual_settings['show_stats'] = url_show_stats
        
        session['flashcard_visual_settings'] = visual_settings
    except Exception:
        pass

    if FlashcardSessionManager.start_new_flashcard_session(set_id, mode):
        # Redirect đến flashcard session (có thể dùng route cũ hoặc practice mới)
        return redirect(url_for('learning.flashcard_learning.flashcard_session'))
    else:
        flash('Không có thẻ nào khả dụng để bắt đầu phiên học.', 'warning')
        return redirect(url_for('learning.vocabulary.set_detail_page', set_id=set_id))


@vocabulary_bp.route('/api/stats/container/<int:container_id>')
@login_required
def api_get_container_stats(container_id):
    """
    API endpoint for comprehensive container statistics.
    Used by the container stats modal on the vocabulary dashboard.
    """
    from .stats.container_stats import VocabularyContainerStats
    
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
        print(f"Error getting container stats: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@vocabulary_bp.route('/item/<int:item_id>/stats')
@login_required
def item_stats_page(item_id):
    """
    [NEW] Detailed statistics page for a single vocabulary item.
    """
    from .stats.item_stats import VocabularyItemStats
    
    stats = VocabularyItemStats.get_item_stats(current_user.user_id, item_id)
    
    if not stats:
        abort(404, description="Item not found")

    if request.args.get('modal') == 'true':
        return render_template('vocabulary/stats/_item_stats_content.html', stats=stats)
        
    return render_template('vocabulary/stats/item_detail.html', stats=stats)

