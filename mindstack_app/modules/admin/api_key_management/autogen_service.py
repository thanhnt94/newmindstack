# File: mindstack_app/modules/admin/api_key_management/autogen_service.py
# Purpose: Auto-generate AI content for quiz and flashcard sets

from flask import current_app
from mindstack_app.models import db, BackgroundTask
from mindstack_app.models.learning import LearningContainer, LearningItem
from mindstack_app.modules.AI.services.ai_manager import get_ai_service
from mindstack_app.modules.AI.logics.prompts import get_formatted_prompt
import time
import threading


def get_sets_with_missing_content(content_type):
    # ... (no change) ...
    try:
        # Map frontend content_type to database container_type
        db_content_type = content_type
        if content_type == 'quiz':
            db_content_type = 'QUIZ_SET'
        elif content_type == 'flashcard':
            db_content_type = 'FLASHCARD_SET'

        # Get containers by type, ordered by title
        containers = LearningContainer.query.filter_by(
            container_type=db_content_type
        ).order_by(LearningContainer.title).all()
        
        result = []
        
        for container in containers:
            # Count total items
            total = LearningItem.query.filter_by(container_id=container.container_id).count()
            
            # Skip containers with no items
            if total == 0:
                continue
            
            # Count items without ai_explanation
            missing = LearningItem.query.filter_by(container_id=container.container_id).filter(
                (LearningItem.ai_explanation == None) | (LearningItem.ai_explanation == '')
            ).count()
            
            result.append({
                'id': container.container_id,
                'name': container.title,
                'subject': container.tags or 'N/A',
                'total': total,
                'missing': missing,
                'to_generate': missing
            })
        
        return {'success': True, 'sets': result}
        
    except Exception as e:
        current_app.logger.error(f"Error getting sets: {str(e)}")
        return {'success': False, 'message': str(e)}


def generate_quiz_explanation(item, ai_client):
    """
    Generate explanation for a quiz question using AI.
    """
    try:
        # Use centralized prompt logic
        prompt = get_formatted_prompt(item, purpose='explanation')
        
        if not prompt:
            return False, "Could not generate prompt (missing data or configuration)"

        response = ai_client.generate_content(
            prompt=prompt,
            feature='explanation',
            context_ref=f"Quiz Item #{item.item_id}"
        )
        
        if isinstance(response, dict):
            if response.get('content'):
                return True, response['content'].strip()
            if response.get('error'):
                return False, response['error']
            return False, "Empty response content"
            
        if isinstance(response, tuple) and len(response) == 2:
            success, data = response
            return success, data

        return False, f"Unknown response format: {type(response)}"
        
    except Exception as e:
        current_app.logger.error(f"Error generating quiz explanation: {str(e)}")
        return False, str(e)


def generate_flashcard_hint(item, ai_client):
    """
    Generate hint for a flashcard using AI.
    """
    try:
        # Use centralized prompt logic
        prompt = get_formatted_prompt(item, purpose='explanation')
        
        if not prompt:
            return False, "Could not generate prompt (missing data or configuration)"

        response = ai_client.generate_content(
            prompt=prompt,
            feature='explanation',
            context_ref=f"Flashcard Item #{item.item_id}"
        )
        
        if isinstance(response, dict):
            if response.get('content'):
                return True, response['content'].strip()
            if response.get('error'):
                return False, response['error']
            return False, "Empty response content"
            
        if isinstance(response, tuple) and len(response) == 2:
            success, data = response
            return success, data
            
        return False, f"Unknown response format: {type(response)}"
        
    except Exception as e:
        current_app.logger.error(f"Error generating flashcard hint: {str(e)}")
        return False, str(e)


def batch_generate_content(content_type, container_id, api_delay=2, max_items=25, task_id=None):
    """
    Batch generate AI content for quiz or flashcard container.
    
    Args:
        content_type: 'quiz' or 'flashcard'
        container_id: ID of the container
        api_delay: Delay between API calls in seconds
        max_items: Maximum number of items to process (-1 for unlimited)
        task_id: ID of the BackgroundTask to update
    
    Returns:
        Dict with results summary
    """
    task = None
    if task_id:
        task = BackgroundTask.query.get(task_id)

    try:
        ai_client = get_ai_service()
        
        results = {
            'total_processed': 0,
            'success_count': 0,
            'error_count': 0,
            'errors': [],
            'items': []  # For progress tracking
        }
        
        # Get items without ai_explanation
        query = LearningItem.query.filter_by(container_id=container_id).filter(
            (LearningItem.ai_explanation == None) | (LearningItem.ai_explanation == '')
        )
        
        if max_items > 0:
            query = query.limit(max_items)
        
        items = query.all()
        total_items = len(items)

        # Update task total
        if task:
            task.total = total_items
            task.progress = 0
            task.status = 'running'
            task.message = f"Starting generation for {total_items} items..."
            db.session.commit()
        
        for idx, item in enumerate(items):
            # Check for stop request
            if task:
                # Refresh task state
                db.session.refresh(task)
                if task.stop_requested:
                    task.status = 'cancelled'
                    task.message = "Task cancelled by user."
                    db.session.commit()
                    return {'success': False, 'message': 'Cancelled by user', 'results': results}

            item_result = {
                'id': item.item_id,
                'index': idx + 1,
                'total': total_items,
                'status': 'processing'
            }
            
            try:
                # Generate content based on type
                if content_type == 'quiz':
                    success, content_or_error = generate_quiz_explanation(item, ai_client)
                else:  # flashcard
                    success, content_or_error = generate_flashcard_hint(item, ai_client)
                
                if success:
                    item.ai_explanation = content_or_error
                    db.session.commit() # Save the generated content
                    
                    results['success_count'] += 1
                    item_result['status'] = 'success'
                    item_result['content'] = content_or_error[:100] + '...' if len(content_or_error) > 100 else content_or_error
                    
                    # Log success briefly
                    if task:
                        task.progress = idx + 1
                        task.message = f"Processed {idx + 1}/{total_items}. Success."
                        db.session.commit()
                else:
                    error_msg = content_or_error
                    results['error_count'] += 1
                    item_result['status'] = 'error'
                    item_result['error'] = error_msg
                    results['errors'].append(f"Item #{item.item_id}: {error_msg}")
                    
                    # Update task with specific error
                    if task:
                        task.progress = idx + 1
                        # Truncate error to fit in message
                        short_err = (error_msg[:50] + '..') if len(error_msg) > 50 else error_msg
                        task.message = f"Processed {idx + 1}/{total_items}. Error: {short_err}"
                        db.session.commit()
                
                results['total_processed'] += 1
                results['items'].append(item_result)
                
                # Delay between API calls (except last one)
                if idx < len(items) - 1 and api_delay > 0:
                    # Smart sleep: Check for stop request every 0.5s during delay
                    start_sleep = time.time()
                    while (time.time() - start_sleep) < api_delay:
                        if task:
                            db.session.refresh(task)
                            if task.stop_requested:
                                # Stop requested during sleep
                                task.status = 'cancelled'
                                task.message = "Task cancelled by user."
                                db.session.commit()
                                return {'success': False, 'message': 'Cancelled by user', 'results': results}
                        
                        # Sleep small chunk
                        sleep_chunk = min(0.5, api_delay - (time.time() - start_sleep))
                        if sleep_chunk > 0:
                            time.sleep(sleep_chunk)
                        else:
                            break
                    
            except Exception as e:
                results['error_count'] += 1
                item_result['status'] = 'error'
                item_result['error'] = str(e)
                results['errors'].append(f"Item #{item.item_id}: {str(e)}")
                results['total_processed'] += 1
                results['items'].append(item_result)
        
        if task:
            task.status = 'completed'
            task.message = f"Completed! Success: {results['success_count']}, Errors: {results['error_count']}"
            db.session.commit()

        return {'success': True, 'results': results}
        
    except Exception as e:
        db.session.rollback()
        if task:
            task.status = 'error'
            task.message = f"Error: {str(e)}"
            db.session.commit()
        current_app.logger.error(f"Error in batch_generate_content: {str(e)}")
        return {'success': False, 'message': str(e)}

def run_autogen_background(app, content_type, container_id, api_delay, max_items, task_id):
    """Wrapper to run batch_generate_content in background thread with app context."""
    with app.app_context():
        batch_generate_content(content_type, container_id, api_delay, max_items, task_id)

