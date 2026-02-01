# File: mindstack_app/modules/learning/collab/routes.py
# Collab Module Routes
# Unified entry point for collaborative learning modes.

from flask import render_template, redirect, url_for
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required

from . import blueprint


@blueprint.route('/')
@login_required
def dashboard():
    """Dashboard cho các chế độ học cộng tác."""
    return render_dynamic_template('modules/learning/collab/default/dashboard.html')
