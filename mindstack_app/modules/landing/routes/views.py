from flask import redirect, url_for
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import current_user
from .. import blueprint

@blueprint.route('/')
def index():
    """
    Trang chủ của ứng dụng.
    Nếu người dùng đã đăng nhập, chuyển hướng đến dashboard.
    """
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.dashboard'))
    return render_dynamic_template('modules/landing/index.html')
