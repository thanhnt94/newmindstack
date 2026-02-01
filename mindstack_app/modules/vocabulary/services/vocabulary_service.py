# File: mindstack_app/modules/vocabulary/services/vocabulary_service.py
from sqlalchemy import or_, func
from flask import render_template_string, current_app, url_for
from mindstack_app.models import (
    db, LearningContainer, LearningItem, User, UserContainerState, LearningProgress
)
from mindstack_app.services.template_service import TemplateService
from mindstack_app.modules.stats.interface import StatsInterface
from ..utils import get_cover_url
import math
from datetime import datetime

class SimplePagination:
    def __init__(self, page, per_page, total_count):
        self.page = int(page)
        self.per_page = int(per_page)
        self.total = int(total_count)
        self.pages = int(math.ceil(self.total / float(self.per_page)))
        self.has_prev = self.page > 1
        self.has_next = self.page < self.pages
        self.prev_num = self.page - 1
        self.next_num = self.page + 1

class VocabularyService:
    @staticmethod
    def get_vocabulary_sets(user_id, category='my', search='', page=1, per_page=10):
        current_app.logger.debug(f"get_vocabulary_sets: user={user_id}, cat={category}, search='{search}'")
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
                learned_container_ids = db.session.query(LearningItem.container_id).join(
                    LearningProgress, LearningItem.item_id == LearningProgress.item_id
                ).filter(LearningProgress.user_id == user_id).distinct()
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
                card_count = LearningItem.query.filter_by(
                    container_id=c.container_id, item_type='FLASHCARD'
                ).count()
                creator = User.query.get(c.creator_user_id)
                sets_data.append({
                    'id': c.container_id,
                    'title': c.title,
                    'description': c.description or '',
                    'cover_image': get_cover_url(c.cover_image),
                    'card_count': card_count,
                    'creator_name': creator.username if creator else 'Unknown',
                    'is_public': c.is_public,
                })
            return {
                'sets': sets_data,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
                'total': pagination.total,
                'page': page
            }
        except Exception as e:
            current_app.logger.error(f"FATAL Error in get_vocabulary_sets: {e}")
            raise e

    @staticmethod
    def get_course_overview_stats(user_id: int, container_id: int, page: int = 1, per_page: int = 12) -> dict:
        """Overview stats delegated to Stats module."""
        return StatsInterface.get_vocab_set_overview_stats(user_id, container_id, page, per_page)

    @staticmethod
    def get_set_detail(user_id, set_id, page=1):
        container = LearningContainer.query.get_or_404(set_id)
        card_count = LearningItem.query.filter_by(container_id=container.container_id, item_type='FLASHCARD').count()
        creator = User.query.get(container.creator_user_id)
        course_stats = VocabularyService.get_course_overview_stats(user_id, set_id, page=page, per_page=12)
        
        pagination_html = ""
        if course_stats and 'pagination' in course_stats:
            p = course_stats['pagination']
            pag_obj = SimplePagination(int(page), 12, int(p['total']))
            version = TemplateService.get_active_version()
            try:
                pagination_template_path = f"{version}/components/pagination/_pagination_mobile.html"
                base_url = f"/learn/vocabulary/api/set/{set_id}"
                tmpl = """
                {% from path import render_pagination_mobile with context %}
                {{ render_pagination_mobile(pagination, set_id=set_id, base_url=base_url) }}
                """
                pagination_html = render_template_string(tmpl, pagination=pag_obj, set_id=set_id, path=pagination_template_path, base_url=base_url)
            except Exception as e:
                current_app.logger.error(f"Error rendering pagination template: {e}")
                pagination_html = f'<div class="flex justify-center gap-4 p-4 bg-yellow-50"><span class="text-sm text-yellow-700">Trang {page} / {pag_obj.pages} (Fallback)</span></div>'
        
        user_obj = User.query.get(user_id)
        user_role = user_obj.user_role if user_obj else 'user'
        return {
            'set': {
                'id': container.container_id, 'title': container.title, 'description': container.description or '',
                'cover_image': get_cover_url(container.cover_image), 'card_count': card_count,
                'creator_name': creator.username if creator else 'Unknown', 'is_public': container.is_public,
                'capabilities': list(container.capability_flags()), 'can_edit': (user_role == 'admin' or container.creator_user_id == user_id),
            },
            'course_stats': course_stats,
            'pagination_html': pagination_html
        }

    @staticmethod
    def get_item_stats(user_id: int, item_id: int) -> dict:
        """Item stats delegated to Stats module."""
        return StatsInterface.get_vocab_item_stats(user_id, item_id)

    @staticmethod
    def save_item_note(user_id, item_id, note_content):
        progress = LearningProgress.query.filter_by(user_id=user_id, item_id=item_id, learning_mode=LearningProgress.MODE_FLASHCARD).first()
        if not progress:
            progress = LearningProgress(user_id=user_id, item_id=item_id, learning_mode=LearningProgress.MODE_FLASHCARD, fsrs_state=LearningProgress.STATE_NEW)
            db.session.add(progress)
        mode_data = dict(progress.mode_data) if progress.mode_data else {}
        mode_data['note'] = note_content
        progress.mode_data = mode_data
        db.session.commit()
        return True
