from mindstack_app import create_app
from mindstack_app.models import db, ApiKey

app = create_app()

with app.app_context():
    print("-" * 50)
    print("DEBUG API KEYS STATUS")
    print("-" * 50)
    
    keys = ApiKey.query.all()
    if not keys:
        print("KHÔNG CÓ API KEY NÀO TRONG DATABASE!")
    
    for k in keys:
        print(f"ID: {k.key_id}")
        print(f"Provider: {k.provider}")
        print(f"Value: {k.key_value[:10]}... (hidden)")
        print(f"Is Active: {k.is_active}")
        print(f"Is Exhausted: {k.is_exhausted}")
        print(f"Last Used: {k.last_used_timestamp}")
        print("-" * 30)

    print("\nAttempting to unlock all Gemini keys...")
    gemini_keys = ApiKey.query.filter_by(provider='gemini').all()
    for k in gemini_keys:
        k.is_exhausted = False
        k.is_active = True
        print(f"-> Unlocking Key ID {k.key_id}")
    
    db.session.commit()
    print("DONE. All Gemini keys have been reset to Active/Not Exhausted.")
