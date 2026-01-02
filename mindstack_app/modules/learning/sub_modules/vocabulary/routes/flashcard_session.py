# File: vocabulary/routes/flashcard_session.py
# Vocabulary Hub - Flashcard Session Routes

from flask import redirect, url_for, flash, request, session, current_app
from flask_login import login_required, current_user

from . import vocabulary_bp
from mindstack_app.models import UserContainerState, db
from mindstack_app.utils.db_session import safe_commit

# Import flashcard engine for session management
from ...flashcard.engine import FlashcardSessionManager


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
        from sqlalchemy.orm.attributes import flag_modified
        
        if not uc_state:
             uc_state = UserContainerState(
                user_id=current_user.user_id, 
                container_id=set_id,
                is_archived=False,
                is_favorite=False,
                settings={}
            )
             db.session.add(uc_state)
             current_app.logger.info(f"[SETTINGS] Created new UserContainerState for container {set_id}")
        
        # Determine if we should auto-save
        new_settings = dict(uc_state.settings or {})
        should_auto_save = new_settings.get('auto_save', True)
        
        current_app.logger.info(f"[SETTINGS] auto_save={should_auto_save}, rating_levels={rating_levels}")
        current_app.logger.info(f"[SETTINGS] Current settings before: {new_settings}")
        
        if 'flashcard' not in new_settings: 
            new_settings['flashcard'] = {}
        
        changed = False

        # 1. Handle Button Count Auto-Save
        if should_auto_save and rating_levels:
            current_button = new_settings['flashcard'].get('button_count')
            current_app.logger.info(f"[SETTINGS] Comparing: current={current_button}, new={rating_levels}")
            if current_button != rating_levels:
                new_settings['flashcard']['button_count'] = rating_levels
                changed = True
                current_app.logger.info(f"[SETTINGS] Updated button_count from {current_button} to {rating_levels}")
        
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
            flag_modified(uc_state, 'settings')  # Force SQLAlchemy to detect JSON change
            db.session.add(uc_state)
            safe_commit(db.session)
            current_app.logger.info(f"[SETTINGS] Saved settings to DB: {new_settings}")
        else:
            current_app.logger.info(f"[SETTINGS] No changes detected, skipping save")
            
    except Exception as e:
        current_app.logger.warning(f"Failed to persist flashcard settings: {e}")
        import traceback
        traceback.print_exc()
            
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
