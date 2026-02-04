"""Kernel Service for low-level content operations."""
from __future__ import annotations
from typing import Any, Optional, Dict, List
from sqlalchemy.orm.attributes import flag_modified
from mindstack_app.models import db, LearningContainer, LearningItem

class ContentKernelService:
    """Provides low-level database operations for learning content."""

    @staticmethod
    def get_container(container_id: int) -> Optional[LearningContainer]:
        return LearningContainer.query.get(container_id)

    @staticmethod
    def get_item(item_id: int) -> Optional[LearningItem]:
        return LearningItem.query.get(item_id)

    @staticmethod
    def create_container(creator_id: int, container_type: str, title: str, 
                         **kwargs) -> LearningContainer:
        container = LearningContainer(
            creator_user_id=creator_id,
            container_type=container_type,
            title=title
        )
        
        for key, value in kwargs.items():
            if hasattr(container, key):
                setattr(container, key, value)
        
        db.session.add(container)
        db.session.commit()
        return container

    @staticmethod
    def update_container(container_id: int, **kwargs) -> Optional[LearningContainer]:
        container = LearningContainer.query.get(container_id)
        if not container:
            return None
        
        for key, value in kwargs.items():
            if hasattr(container, key):
                setattr(container, key, value)
        
        if 'settings' in kwargs:
            flag_modified(container, 'settings')
        
        db.session.commit()
        return container

    @staticmethod
    def delete_container(container_id: int) -> bool:
        container = LearningContainer.query.get(container_id)
        if container:
            db.session.delete(container)
            db.session.commit()
            return True
        return False

    @staticmethod
    def create_item(container_id: int, item_type: str, content: Dict, 
                    order: int = 0, custom_data: Dict = None, 
                    ai_explanation: str = None) -> LearningItem:
        item = LearningItem(
            container_id=container_id,
            item_type=item_type,
            content=content,
            order_in_container=order,
            custom_data=custom_data,
            ai_explanation=ai_explanation
        )
        if hasattr(item, 'update_search_text'):
            item.update_search_text()
            
        db.session.add(item)
        db.session.commit()
        
        # Emit signal
        try:
            from ..signals import content_created
            container = LearningContainer.query.get(container_id)
            user_id = container.creator_user_id if container else None
            
            content_created.send(
                item,
                item_id=item.item_id,
                item_type=item_type,
                container_id=container_id,
                user_id=user_id
            )
        except Exception as e:
            # Don't fail the operation if signal fails
            pass
            
        return item

    @staticmethod
    def update_item(item_id: int, content: Dict = None, order: int = None, 
                    custom_data: Dict = None, ai_explanation: str = None) -> Optional[LearningItem]:
        item = LearningItem.query.get(item_id)
        if not item:
            return None
        
        changes = {}
        if content is not None:
            item.content = content
            flag_modified(item, 'content')
            changes['content'] = True
        if order is not None:
            item.order_in_container = order
            changes['order'] = True
        if custom_data is not None:
            item.custom_data = custom_data
            flag_modified(item, 'custom_data')
            changes['custom_data'] = True
        if ai_explanation is not None:
            item.ai_explanation = ai_explanation
            changes['ai_explanation'] = True
            
        if hasattr(item, 'update_search_text'):
            item.update_search_text()
            
        db.session.commit()
        
        # Emit signal
        try:
            from ..signals import content_updated
            container = item.container
            user_id = container.creator_user_id if container else None
            
            content_updated.send(
                item,
                item_id=item.item_id,
                item_type=item.item_type,
                changes=changes,
                container_id=item.container_id,
                user_id=user_id
            )
        except Exception:
            pass
            
        return item

    @staticmethod
    def delete_item(item_id: int) -> bool:
        item = LearningItem.query.get(item_id)
        if item:
            # Capture data for signal before deletion
            item_type = item.item_type
            container_id = item.container_id
            container = item.container
            user_id = container.creator_user_id if container else None
            
            db.session.delete(item)
            db.session.commit()
            
            # Emit signal
            try:
                from ..signals import content_deleted
                content_deleted.send(
                    None,  # Sender is None because object is deleted
                    item_id=item_id,
                    item_type=item_type,
                    container_id=container_id,
                    user_id=user_id
                )
            except Exception:
                pass
                
            return True
        return False

    @staticmethod
    def reorder_items(container_id: int, item_type: str, ordered_ids: List[int]) -> bool:
        """Update order_in_container for multiple items at once."""
        items = LearningItem.query.filter_by(container_id=container_id, item_type=item_type).all()
        item_map = {item.item_id: item for item in items}
        
        for idx, item_id in enumerate(ordered_ids, start=1):
            if item_id in item_map:
                item_map[item_id].order_in_container = idx
        
        db.session.commit()
        return True
