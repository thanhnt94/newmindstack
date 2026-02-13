import flask
from flask import render_template
from typing import Dict, Any, Optional

class FlashcardRenderer:
    """
    Handles backend rendering of flashcard HTML fragments.
    Moves logic away from JS template literals to Jinja2.
    """
    
    @staticmethod
    def render_item(item, stats: Dict[str, Any], mode='flashcard', display_settings: Optional[Dict] = None) -> Dict[str, str]:
        """
        Renders front and back HTML for a single flashcard item.
        'item' can be a FlashcardItem model or a dictionary.
        """
        # Display settings defaults
        ds = display_settings or {}
        
        # Prepare context for Jinja
        item_data = {
            'id': item.id if hasattr(item, 'id') else item.get('id'),
            'front_text': item.front_text if hasattr(item, 'front_text') else item.get('front_text'),
            'back_text': item.back_text if hasattr(item, 'back_text') else item.get('back_text'),
            'front_image': item.front_image if hasattr(item, 'front_image') else item.get('front_image'),
            'back_image': item.back_image if hasattr(item, 'back_image') else item.get('back_image'),
            'front_audio_url': item.front_audio_url if hasattr(item, 'front_audio_url') else item.get('front_audio_url'),
            'back_audio_url': item.back_audio_url if hasattr(item, 'back_audio_url') else item.get('back_audio_url'),
            'has_front_audio': item.has_front_audio if hasattr(item, 'has_front_audio') else item.get('has_front_audio'),
            'has_back_audio': item.has_back_audio if hasattr(item, 'has_back_audio') else item.get('has_back_audio'),
            'front_audio_content': item.front_audio_content if hasattr(item, 'front_audio_content') else item.get('front_audio_content'),
            'back_audio_content': item.back_audio_content if hasattr(item, 'back_audio_content') else item.get('back_audio_content'),
            
            # Display alignment/bold from settings
            'front_align': ds.get('front_align', 'none'),
            'back_align': ds.get('back_align', 'none'),
            'force_bold_front': ds.get('force_bold_front', False),
            'force_bold_back': ds.get('force_bold_back', False),
            
            # Category/Custom
            'card_category': item.category if hasattr(item, 'category') else item.get('category', 'default'),
            'buttons_html': item.buttons_html if hasattr(item, 'buttons_html') else item.get('buttons_html', '')
        }
        
        context = {
            'item': item_data,
            'stats': stats,
            'mode': mode,
            'can_edit': ds.get('can_edit', False),
            'edit_url': ds.get('edit_url', ''),
            'is_media_hidden': ds.get('is_media_hidden', False),
            'is_audio_autoplay': ds.get('is_audio_autoplay', False)
        }
        
        # We use separate partials for front and back
        try:
            # Note: We assume these templates exist in the current theme path
            # Theme: aura_mobile
            html_front = render_template('aura_mobile/modules/vocab_flashcard/partials/card_front.html', **context)
            html_back = render_template('aura_mobile/modules/vocab_flashcard/partials/card_back.html', **context)
            
            # Construct full container HTML
            full_html = f"""
            <div class="flashcard-card-container">
                <div class="js-flashcard-card flashcard-card flashcard-card--{item_data['card_category']}" data-card-category="{item_data['card_category']}">
                    {html_front}
                    {html_back}
                </div>
            </div>
            """
            
            return {
                'front': html_front,
                'back': html_back,
                'full_html': full_html
            }
        except Exception as e:
            # Fallback or error logging
            print(f"[FlashcardRenderer] Rendering error: {e}")
            return {
                'front': f'<div class="error">Front error: {str(e)}</div>',
                'back': f'<div class="error">Back error: {str(e)}</div>',
                'full_html': f'<div class="error">Rendering error: {str(e)}</div>'
            }
