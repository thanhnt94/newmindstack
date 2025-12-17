from flask import render_template, redirect, url_for
from flask_login import current_user
from . import landing_bp

@landing_bp.route('/')
def index():
    """
    Trang chủ của ứng dụng.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    return render_template('landing/index.html')
