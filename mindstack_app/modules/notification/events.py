"""
Event Handlers for Notification Module.

Listens to signals from other modules and creates notifications accordingly.
This enables event-driven notifications - no other module needs to import
NotificationService directly.
"""
from flask import current_app
from mindstack_app.core.signals import content_created, score_awarded


@content_created.connect
def on_content_created(sender, **kwargs):
    """
    Notify when new content is created/imported.
    
    Only creates notifications for significant events (not every import).
    
    Expected kwargs:
        - user_id: int
        - content_type: str ('flashcard_import', 'course', etc.)
        - content_id: int
        - title: str
        - items_created: int (optional)
    """
    from .services import NotificationService
    
    user_id = kwargs.get('user_id')
    content_type = kwargs.get('content_type', '')
    title = kwargs.get('title', 'Nội dung')
    items_created = kwargs.get('items_created', 0)
    content_id = kwargs.get('content_id')
    
    if not user_id:
        return
    
    try:
        # Only notify for significant imports (more than 5 items)
        if content_type == 'flashcard_import' and items_created > 0:
            NotificationService.create_notification(
                user_id=user_id,
                title="Import thành công!",
                message=f"Đã thêm {items_created} thẻ mới vào bộ thẻ '{title}'.",
                type='CONTENT',
                link=f'/flashcard/set/{content_id}'
            )
            current_app.logger.debug(f"[Notification] Created import notification for user {user_id}")
            
    except Exception as e:
        current_app.logger.error(f"[Notification] Error creating notification: {e}", exc_info=True)


@score_awarded.connect
def on_score_awarded(sender, **kwargs):
    """
    Handle score_awarded signal.
    
    Only creates notifications for significant score milestones,
    not every point earned (to avoid notification spam).
    
    Expected kwargs:
        - user_id: int
        - amount: int
        - reason: str
        - new_total: int
        - item_type: str
    """
    from .services import NotificationService
    
    user_id = kwargs.get('user_id')
    amount = kwargs.get('amount', 0)
    new_total = kwargs.get('new_total', 0)
    
    if not user_id or not new_total:
        return
    
    try:
        # Notify on milestone achievements (every 100, 500, 1000 points, etc.)
        milestones = [100, 250, 500, 1000, 2500, 5000, 10000]
        
        for milestone in milestones:
            # Check if user just crossed this milestone
            if new_total >= milestone > (new_total - amount):
                NotificationService.create_notification(
                    user_id=user_id,
                    title=f"Cột mốc {milestone} điểm!",
                    message=f"Chúc mừng! Bạn đã đạt {milestone} điểm tổng cộng. Tiếp tục cố gắng nhé!",
                    type='ACHIEVEMENT',
                    link='/profile'
                )
                current_app.logger.info(f"[Notification] Milestone {milestone} reached for user {user_id}")
                break  # Only one notification per score update
                
    except Exception as e:
        current_app.logger.error(f"[Notification] Error in score notification: {e}", exc_info=True)


from mindstack_app.core.signals import user_registered

@user_registered.connect
def on_user_registered(sender, user, **kwargs):
    """
    Send welcome notification to new users.
    """
    from .services import NotificationService
    
    try:
        NotificationService.create_notification(
            user_id=user.user_id,
            title="Chào mừng đến với MindStack!",
            message="Cảm ơn bạn đã tham gia. Hãy bắt đầu hành trình học tập bằng cách tạo bộ thẻ đầu tiên nhé!",
            type='SYSTEM',
            link='/dashboard'
        )
        current_app.logger.info(f"[Notification] Sent welcome notification to user {user.user_id}")
    except Exception as e:
        current_app.logger.error(f"[Notification] Error sending welcome notification: {e}", exc_info=True)
