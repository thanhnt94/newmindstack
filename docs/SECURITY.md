# MindStack Security Guide

## Overview

Hướng dẫn bảo mật cho MindStack application.

---

## 🔐 Authentication

### Flask-Login

MindStack sử dụng Flask-Login cho session-based authentication:

```python
from flask_login import LoginManager, login_user, logout_user, current_user, login_required

login_manager = LoginManager()
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
```

### Password Hashing

```python
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    password_hash = db.Column(db.String(256))
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
```

---

## 👥 Authorization

### User Roles

| Role | Access Level |
|------|--------------|
| `admin` | Full access, manage users |
| `user` | Standard access |
| `free` | Limited features |

### Role Checking

```python
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))
        if current_user.user_role != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/admin/users')
@admin_required
def manage_users():
    pass
```

### Resource Access Control

```python
# Check container ownership
def can_edit_container(user_id, container_id):
    container = LearningContainer.query.get(container_id)
    if not container:
        return False
    
    # Owner can edit
    if container.creator_user_id == user_id:
        return True
    
    # Admin can edit
    user = User.query.get(user_id)
    if user and user.user_role == 'admin':
        return True
    
    # Contributor with editor permission
    contributor = ContainerContributor.query.filter_by(
        container_id=container_id,
        user_id=user_id,
        permission_level='editor'
    ).first()
    return contributor is not None
```

---

## 🛡️ CSRF Protection

### Flask-WTF

```python
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()

# In app factory
csrf.init_app(app)
```

### In Templates

```jinja
<form method="POST">
    {{ form.csrf_token }}
    <!-- form fields -->
</form>
```

### AJAX Requests

```javascript
// Get CSRF token from meta tag
const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

fetch('/api/endpoint', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken
    },
    body: JSON.stringify(data)
});
```

---

## 🔒 Session Security

### Configuration

```python
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')  # Required!
    
    # Session settings
    SESSION_COOKIE_SECURE = True      # HTTPS only
    SESSION_COOKIE_HTTPONLY = True    # No JS access
    SESSION_COOKIE_SAMESITE = 'Lax'   # CSRF protection
    
    # Permanent session
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
```

### Generate Secret Key

```python
import secrets
print(secrets.token_hex(32))
```

---

## 🗄️ Database Security

### SQL Injection Prevention

**Always use ORM queries:**

```python
# ✅ Good - ORM prevents SQL injection
user = User.query.filter_by(username=username).first()

# ✅ Good - Parameterized query
result = db.session.execute(
    text("SELECT * FROM users WHERE username = :username"),
    {"username": username}
)

# ❌ Bad - String formatting (SQL injection risk!)
result = db.session.execute(f"SELECT * FROM users WHERE username = '{username}'")
```

### Sensitive Data

```python
# Never log sensitive data
current_app.logger.info(f"User {user.username} logged in")  # ✅
current_app.logger.info(f"Password: {password}")  # ❌

# Mask API keys in logs
def mask_key(key):
    if len(key) > 8:
        return key[:4] + '***' + key[-4:]
    return '***'
```

---

## 🌐 Input Validation

### Form Validation

```python
from wtforms import StringField, validators

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[
        validators.DataRequired(),
        validators.Length(min=3, max=50),
        validators.Regexp('^[A-Za-z0-9_]+$', message='Only alphanumeric and underscore')
    ])
    
    password = PasswordField('Password', validators=[
        validators.DataRequired(),
        validators.Length(min=8)
    ])
```

### API Input Validation

```python
@bp.route('/api/submit', methods=['POST'])
def submit():
    data = request.get_json()
    
    # Validate required fields
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    item_id = data.get('item_id')
    if not isinstance(item_id, int) or item_id <= 0:
        return jsonify({'error': 'Invalid item_id'}), 400
    
    quality = data.get('quality')
    if quality not in range(0, 6):
        return jsonify({'error': 'Quality must be 0-5'}), 400
    
    # Process valid data...
```

---

## 🖥️ XSS Prevention

### Template Auto-Escaping

Jinja2 auto-escapes by default:

```jinja
{# Auto-escaped (safe) #}
{{ user_input }}

{# Only use safe when you KNOW content is safe #}
{{ trusted_html | safe }}
```

### Content Security Policy

```python
@app.after_request
def add_security_headers(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' cdn.example.com; "
        "style-src 'self' 'unsafe-inline' fonts.googleapis.com; "
        "img-src 'self' data: https:; "
        "font-src 'self' fonts.gstatic.com; "
    )
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response
```

---

## 📁 File Upload Security

### Allowed Extensions

```python
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp3', 'wav'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
```

### Secure Filename

```python
from werkzeug.utils import secure_filename
import uuid

def save_uploaded_file(file):
    if file and allowed_file(file.filename):
        # Generate unique filename
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4()}.{ext}"
        
        # Secure the path
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return filename
    return None
```

### File Size Limits

```python
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
```

---

## 🔑 API Key Security

### Storage

API keys được lưu trong database, không trong code:

```python
class ApiKey(db.Model):
    key_id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50))
    key_value = db.Column(db.Text)  # Encrypted in production
    is_active = db.Column(db.Boolean, default=True)
```

### Access Pattern

```python
# Never expose keys to frontend
@bp.route('/api/ai/explain')
@login_required
def explain():
    # Key is used server-side only
    ai_service = get_ai_service()
    result = ai_service.generate(prompt)
    return jsonify(result)
```

---

## 📊 Logging Security Events

```python
import logging

security_logger = logging.getLogger('security')

# Log security events
def log_login_attempt(username, success, ip_address):
    if success:
        security_logger.info(f"Login success: {username} from {ip_address}")
    else:
        security_logger.warning(f"Login failed: {username} from {ip_address}")

def log_permission_denied(user_id, resource, action):
    security_logger.warning(
        f"Permission denied: user={user_id}, resource={resource}, action={action}"
    )
```

---

## ✅ Security Checklist

### Development

- [ ] SECRET_KEY is set (not default)
- [ ] Debug mode disabled
- [ ] CSRF protection enabled
- [ ] Input validation on all forms
- [ ] SQL injection prevention (use ORM)

### Production

- [ ] HTTPS enforced
- [ ] Secure session cookies
- [ ] Security headers configured
- [ ] File upload restrictions
- [ ] Rate limiting enabled
- [ ] Logging configured
- [ ] Backups encrypted

---

## 📚 References

- [Flask Security](https://flask.palletsprojects.com/en/2.0.x/security/)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask-Login](https://flask-login.readthedocs.io/)
- [Flask-WTF CSRF](https://flask-wtf.readthedocs.io/en/1.0.x/csrf/)
