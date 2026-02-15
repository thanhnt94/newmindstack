from mindstack_app.models import (
    db, LearningContainer, LearningItem, User, UserContainerState
)

from mindstack_app.modules.fsrs.interface import FSRSInterface as FsrsInterface
from sqlalchemy import or_, func
from flask import current_app
from mindstack_app.modules.stats.interface import StatsInterface
from ..logics.cover_logic import get_cover_url
from ..schemas import VocabItemDTO, VocabSetDTO, VocabSetDetailDTO
import math
from datetime import datetime, timezone

class VocabularyService:
    @staticmethod
    def get_vocabulary_sets(user_id, category='my', search='', page=1, per_page=10):
        """Get filtered vocabulary sets with pagination."""
        try:
            query = LearningContainer.query.filter(LearningContainer.container_type == 'FLASHCARD_SET')
            if search:
                query = query.filter(or_(
                    LearningContainer.title.ilike(f'%{search}%'),
                    LearningContainer.description.ilike(f'%{search}%')
                ))
            
            if category == 'my':
                query = query.filter(LearningContainer.creator_user_id == user_id)
            elif category == 'learning':
                # REFACTORED: Use FsrsInterface to get learned items/containers
                learned_item_ids = FsrsInterface.get_learned_item_ids(user_id)
                # Find containers that contain these items
                # Optimization: We can ask FSRS for container_ids if supported, 
                # but currently we map item_ids -> container_ids via SQL here or 
                # assume FsrsInterface returns what we need.
                # Since the instruction said "get list item_ids, then filter LearningContainer",
                # we need to join locally with LearningItem to find distinct containers.
                
                learned_container_ids = db.session.query(LearningItem.container_id).filter(
                    LearningItem.item_id.in_(learned_item_ids)
                ).distinct()
                
                query = query.filter(LearningContainer.container_id.in_(learned_container_ids))

            elif category in ['public', 'explore']:
                query = query.filter(LearningContainer.is_public == True)
            elif category == 'favorite':
                query = query.join(UserContainerState).filter(
                    UserContainerState.user_id == user_id,
                    UserContainerState.is_favorite == True
                )
            
            pagination = query.order_by(LearningContainer.updated_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            sets_data = []
            for c in pagination.items:
                card_count = LearningItem.query.filter(
                    LearningItem.container_id == c.container_id,
                    LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
                ).count()
                creator = User.query.get(c.creator_user_id)
                
                sets_data.append(VocabSetDTO(
                    id=c.container_id,
                    title=c.title,
                    description=c.description or '',
                    cover_image=get_cover_url(c.cover_image),
                    card_count=card_count,
                    creator_name=creator.username if creator else 'Unknown',
                    is_public=c.is_public,
                    ai_capabilities=list(c.capability_flags())
                ))

                
            return {
                'sets': sets_data,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
                'total': pagination.total,
                'page': page
            }
        except Exception as e:
            current_app.logger.error(f"Error in get_vocabulary_sets: {e}")
            raise e

    @staticmethod
    def get_set_detail(user_id: int, set_id: int, page: int = 1, sort_by: str = 'default', filter_mode: str = 'all') -> VocabSetDetailDTO:
        """Get comprehensive details and stats for a set."""
        container = LearningContainer.query.get_or_404(set_id)
        card_count = LearningItem.query.filter(
            LearningItem.container_id == container.container_id,
            LearningItem.item_type.in_(['FLASHCARD', 'VOCABULARY'])
        ).count()
        creator = User.query.get(container.creator_user_id)
        
        # Stats delegated to Stats module
        course_stats = StatsInterface.get_vocab_set_overview_stats(user_id, set_id, page, 12, sort_by=sort_by, filter_mode=filter_mode)
        
        user_obj = User.query.get(user_id)
        user_role = user_obj.user_role if user_obj else 'user'
        can_edit = (user_role == 'admin' or container.creator_user_id == user_id)
        
        set_info = VocabSetDTO(
            id=container.container_id,
            title=container.title,
            description=container.description or '',
            cover_image=get_cover_url(container.cover_image),
            card_count=card_count,
            creator_name=creator.username if creator else 'Unknown',
            is_public=container.is_public,
            ai_capabilities=list(container.capability_flags())
        )

        
        return VocabSetDetailDTO(
            set_info=set_info,
            stats=course_stats,
            capabilities=list(container.capability_flags()),
            can_edit=can_edit
        )

    @staticmethod
    def get_item_stats(user_id: int, item_id: int) -> dict:
        """Fetch item statistics."""
        return StatsInterface.get_vocab_item_stats(user_id, item_id)

    @staticmethod
    def get_user_container_settings(user_id: int, container_id: int) -> dict:
        """Fetch user-specific settings for a container."""
        uc_state = UserContainerState.query.filter_by(
            user_id=user_id, 
            container_id=container_id
        ).first()
        return uc_state.settings if uc_state and uc_state.settings else {}

    @staticmethod
    def save_item_note(user_id, item_id, note_content):
        """Save user personal note for a learning item."""
        # REFACTORED: Delegate to FsrsInterface
        return FsrsInterface.save_item_note(user_id, item_id, note_content)