from flask import redirect, url_for
from mindstack_app.core.templating import render_template
from flask_login import current_user
from . import landing_bp

@landing_bp.route('/')
def index():
    """
    Trang chủ của ứng dụng.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    return render_template('pages/landing/default/index.html')
