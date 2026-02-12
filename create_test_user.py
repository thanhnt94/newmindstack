
from mindstack_app import create_app, db
from mindstack_app.models import User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():
    email = "test_user_frozen@example.com"
    password = "password123"
    
    user = User.query.filter_by(email=email).first()
    if user:
        print(f"User {email} already exists. Resetting password...")
        user.password_hash = generate_password_hash(password)
        db.session.commit()
        print("Password reset.")
    else:
        print(f"Creating user {email}...")
        new_user = User(
            email=email,
            password_hash=generate_password_hash(password),
            username="TestUserFrozen",
            user_role='admin' # Give admin just in case
        )
        db.session.add(new_user)
        db.session.commit()
        print("User created.")
