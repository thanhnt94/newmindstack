from mindstack_app import create_app
from mindstack_app.modules.vocabulary.services.vocabulary_service import VocabularyService
from mindstack_app.models import User

app = create_app()
with app.app_context():
    user_id = 1
    set_id = 4
    page = 1
    
    print(f"--- Testing get_set_detail for set {set_id} ---")
    try:
        result = VocabularyService.get_set_detail(user_id, set_id, page=page)
        print("Success!")
        print(f"Set Title: {result['set']['title']}")
        print(f"Items count: {len(result['course_stats']['items'])}")
        print(f"Pagination HTML length: {len(result['pagination_html'])}")
        if result['pagination_html']:
            print(f"Start of HTML: {result['pagination_html'][:100]}...")
        if "(Fallback)" in result['pagination_html']:
            print("!!! FALLBACK PAGINATION USED")
    except Exception as e:
        print(f"\n!!! ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
