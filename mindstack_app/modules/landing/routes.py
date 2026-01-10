from flask import render_template, redirect, url_for
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import current_user
from . import landing_bp

@landing_bp.route('/')
def index():
    """
    Trang chủ của ứng dụng.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    return render_dynamic_template('pages/landing/index.html')
