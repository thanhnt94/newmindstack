# File: mindstack_app/modules/admin/api_key_management/autogen_service.py
# Purpose: Auto-generate AI content for quiz and flashcard sets

from flask import current_app
from ....models import db, BackgroundTask
from ....models.learning import LearningContainer, LearningItem
from ...ai_services.service_manager import get_ai_service
import time
import threading


def get_sets_with_missing_content(content_type):
    """
    Get list of quiz/flashcard containers with missing content count.
    
    Args:
        content_type: 'quiz' or 'flashcard'
    
    Returns:
        List of dicts with container info and missing content counts
    """
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
    
    Args:
        item: LearningItem object with quiz content
        ai_client: AI service client
    
    Returns:
        tuple: (success, content_or_error)
    """
    try:
        content = item.content
        if not isinstance(content, dict):
            return False, "Invalid content format"
        
        question_text = content.get('question', '')
        options = content.get('options', {})
        correct_answer = content.get('correct_answer', '')
        
        # Build options text
        options_text = '\n'.join([f"{key}) {value}" for key, value in options.items()])
        
        prompt = f"""Tạo explanation (giải thích) cho câu hỏi trắc nghiệm sau:

Câu hỏi: {question_text}
{options_text}

Đáp án đúng: {correct_answer}

Hãy viết explanation ngắn gọn (2-3 câu) giải thích tại sao đáp án này đúng."""

        # generate_content usually returns dict or object, 
        # but let's check how the client wrapper behaves.
        # Looking at GeminiClient (previous read), it returns (True, text) or (False, error).
        # Wait, get_ai_service returns HybridAIClient or GeminiClient.
        # GeminiClient.generate_content returns (True, result) or (False, error_msg).
        # HybridAIClient likely follows suit or returns result dict.
        # Let's check HybridAIClient later if needed, but safe assumption is we need to handle whatever it returns.
        # Actually, let's look at previous code:
        # response = ai_client.generate_content(...)
        # if response and response.get('content'): ...
        
        # This implies ai_client.generate_content returns a DICT like {'content': ...}.
        # My reading of GeminiClient showed it returning (True, result)...
        # There might be a discrepancy. 
        # Let's check HybridAIClient or assume the old code was correct about the return type being a DICT.
        # "if response and response.get('content'):"
        
        response = ai_client.generate_content(
            prompt=prompt,
            item_info=f"Quiz Item #{item.item_id}"
        )
        
        # Adapting to potentially different return types from different clients
        # If it returns a dict (Standard Service Wrapper):
        if isinstance(response, dict):
            if response.get('content'):
                return True, response['content'].strip()
            if response.get('error'):
                return False, response['error']
            return False, "Empty response content"
            
        # If it returns a tuple (GeminiClient raw):
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
    
    Args:
        item: LearningItem object with flashcard content
        ai_client: AI service client
    
    Returns:
        tuple: (success, content_or_error)
    """
    try:
        content = item.content
        if not isinstance(content, dict):
            return False, "Invalid content format"
        
        question = content.get('question', '')
        answer = content.get('answer', '')
        
        prompt = f"""Tạo hint (gợi ý) cho flashcard sau:

Mặt trước (Question): {question}
Mặt sau (Answer): {answer}

Hãy viết hint ngắn gọn (1-2 câu) giúp người học nhớ được đáp án mà không tiết lộ trực tiếp."""

        response = ai_client.generate_content(
            prompt=prompt,
            item_info=f"Flashcard Item #{item.item_id}"
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

