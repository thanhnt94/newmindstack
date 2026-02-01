# File: mindstack_app/modules/vocabulary/services/vocabulary_service.py
from sqlalchemy import or_
from flask import render_template_string
from mindstack_app.models import (
    db, LearningContainer, LearningItem, User, UserContainerState, LearningProgress
)
from mindstack_app.services.template_service import TemplateService
import math

class SimplePagination:
    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total = total_count
        self.pages = int(math.ceil(total_count / float(per_page)))
        self.has_prev = page > 1
        self.has_next = page < self.pages

from ..utils import get_cover_url

class VocabularyService:
    @staticmethod
    def get_vocabulary_sets(user_id, category='my', search='', page=1, per_page=10):
        
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

    @staticmethod
    def get_set_detail(user_id, set_id, page=1):
        """Lấy thông tin chi tiết một bộ thẻ và tiến độ SRS."""
        container = LearningContainer.query.get_or_404(set_id)
        
        card_count = LearningItem.query.filter_by(
            container_id=container.container_id, item_type='FLASHCARD'
        ).count()
        
        creator = User.query.get(container.creator_user_id)
        
        # Get Course Stats via Logic Layer
        from ..logics.stats_logic import get_course_overview_stats
        course_stats = get_course_overview_stats(user_id, set_id, page=page, per_page=12)
        
        # Render Pagination HTML (Server-side component)
        pagination_html = ""
        if course_stats and 'pagination' in course_stats:
            p = course_stats['pagination']
            pag_obj = SimplePagination(int(page), 12, int(p['total']))
            version = TemplateService.get_active_version()
            
            tmpl = """
            {% from version ~ '/includes/pagination/_pagination_mobile.html' import render_pagination_mobile %}
            {{ render_pagination_mobile(pagination, set_id=set_id) }}
            """
            pagination_html = render_template_string(tmpl, pagination=pag_obj, set_id=set_id, version=version)

        return {
            'set': {
                'id': container.container_id,
                'title': container.title,
                'description': container.description or '',
                'cover_image': get_cover_url(container.cover_image),
                'card_count': card_count,
                'creator_name': creator.username if creator else 'Unknown',
                'is_public': container.is_public,
                'capabilities': list(container.capability_flags()),
                'can_edit': (User.query.get(user_id).user_role == 'admin' or container.creator_user_id == user_id),
            },
            'course_stats': course_stats,
            'pagination_html': pagination_html
        }

    @staticmethod
    def save_item_note(user_id, item_id, note_content):
        """Lưu ghi chú cá nhân cho một từ vựng."""
        progress = LearningProgress.query.filter_by(
            user_id=user_id,
            item_id=item_id,
            learning_mode=LearningProgress.MODE_FLASHCARD
        ).first()
        
        if not progress:
            progress = LearningProgress(
                user_id=user_id,
                item_id=item_id,
                learning_mode=LearningProgress.MODE_FLASHCARD,
                status='new'
            )
            db.session.add(progress)
            
        mode_data = dict(progress.mode_data) if progress.mode_data else {}
        mode_data['note'] = note_content
        progress.mode_data = mode_data
        db.session.commit()
        return True
