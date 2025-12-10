# File: mindstack_app/modules/admin/api_key_management/autogen_service.py
# Purpose: Auto-generate AI content for quiz and flashcard sets

from flask import current_app
from ....models import db
from ....models.learning import LearningContainer, LearningItem
from ...ai_services.service_manager import get_ai_service
import time


def get_sets_with_missing_content(content_type):
    """
    Get list of quiz/flashcard containers with missing content count.
    
    Args:
        content_type: 'quiz' or 'flashcard'
    
    Returns:
        List of dicts with container info and missing content counts
    """
    try:
        # Get containers by type, ordered by title
        containers = LearningContainer.query.filter_by(
            container_type=content_type
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
        Generated explanation text or None
    """
    try:
        content = item.content
        if not isinstance(content, dict):
            return None
        
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

        response = ai_client.generate_content(
            prompt=prompt,
            context_info=f"Quiz Item #{item.item_id}"
        )
        
        if response and response.get('content'):
            return response['content'].strip()
        return None
        
    except Exception as e:
        current_app.logger.error(f"Error generating quiz explanation: {str(e)}")
        return None


def generate_flashcard_hint(item, ai_client):
    """
    Generate hint for a flashcard using AI.
    
    Args:
        item: LearningItem object with flashcard content
        ai_client: AI service client
    
    Returns:
        Generated hint text or None
    """
    try:
        content = item.content
        if not isinstance(content, dict):
            return None
        
        question = content.get('question', '')
        answer = content.get('answer', '')
        
        prompt = f"""Tạo hint (gợi ý) cho flashcard sau:

Mặt trước (Question): {question}
Mặt sau (Answer): {answer}

Hãy viết hint ngắn gọn (1-2 câu) giúp người học nhớ được đáp án mà không tiết lộ trực tiếp."""

        response = ai_client.generate_content(
            prompt=prompt,
            context_info=f"Flashcard Item #{item.item_id}"
        )
        
        if response and response.get('content'):
            return response['content'].strip()
        return None
        
    except Exception as e:
        current_app.logger.error(f"Error generating flashcard hint: {str(e)}")
        return None


def batch_generate_content(content_type, container_id, api_delay=2, max_items=25):
    """
    Batch generate AI content for quiz or flashcard container.
    
    Args:
        content_type: 'quiz' or 'flashcard'
        container_id: ID of the container
        api_delay: Delay between API calls in seconds
        max_items: Maximum number of items to process (-1 for unlimited)
    
    Returns:
        Dict with results summary
    """
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
        
        for idx, item in enumerate(items):
            item_result = {
                'id': item.item_id,
                'index': idx + 1,
                'total': total_items,
                'status': 'processing'
            }
            
            try:
                # Generate content based on type
                if content_type == 'quiz':
                    generated_content = generate_quiz_explanation(item, ai_client)
                else:  # flashcard
                    generated_content = generate_flashcard_hint(item, ai_client)
                
                if generated_content:
                    item.ai_explanation = generated_content
                    db.session.commit()
                    results['success_count'] += 1
                    item_result['status'] = 'success'
                    item_result['content'] = generated_content[:100] + '...' if len(generated_content) > 100 else generated_content
                else:
                    results['error_count'] += 1
                    item_result['status'] = 'error'
                    item_result['error'] = 'No content returned from AI'
                    results['errors'].append(f"Item #{item.item_id}: No content returned")
                
                results['total_processed'] += 1
                results['items'].append(item_result)
                
                # Delay between API calls (except last one)
                if idx < len(items) - 1:
                    time.sleep(api_delay)
                    
            except Exception as e:
                results['error_count'] += 1
                item_result['status'] = 'error'
                item_result['error'] = str(e)
                results['errors'].append(f"Item #{item.item_id}: {str(e)}")
                results['total_processed'] += 1
                results['items'].append(item_result)
        
        return {'success': True, 'results': results}
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in batch_generate_content: {str(e)}")
        return {'success': False, 'message': str(e)}
