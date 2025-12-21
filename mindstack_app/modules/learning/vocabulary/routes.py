# File: mindstack_app/modules/learning/vocabulary/routes.py
# Vocabulary Learning Hub Routes

from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import or_

from . import vocabulary_bp
from mindstack_app.models import (
    LearningContainer, LearningItem, User, UserContainerState
)


@vocabulary_bp.route('/')
@vocabulary_bp.route('/dashboard')
@login_required
def dashboard():
    """Main vocabulary learning hub dashboard."""
    return render_template('vocabulary/dashboard/index.html')


@vocabulary_bp.route('/api/sets')
@login_required  
def api_get_sets():
    """API to get vocabulary sets with search and category filter."""
    search = request.args.get('q', '').strip()
    category = request.args.get('category', 'my')  # my, learning, explore
    page = request.args.get('page', 1, type=int)
    per_page = 12
    
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
    """Deep link to specific set detail."""
    return render_template('vocabulary/dashboard/index.html', active_set_id=set_id)


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
    try:
        from .memrise.logic import get_course_overview_stats
        course_stats = get_course_overview_stats(current_user.user_id, set_id, page=page, per_page=12)
    except Exception as e:
        print(f"ERROR calculating course stats for set {set_id}: {e}")
        # Return empty stats or handle gracefully so page doesn't crash
        course_stats = None

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
        },
        'course_stats': course_stats
    })
