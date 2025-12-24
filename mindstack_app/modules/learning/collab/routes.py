# File: mindstack_app/modules/learning/collab/routes.py
# Collab Module Routes
# Unified entry point for collaborative learning modes.

from flask import render_template, redirect, url_for
from flask_login import login_required

from . import collab_bp


@collab_bp.route('/')
@login_required
def dashboard():
    """Dashboard cho các chế độ học cộng tác."""
    return render_template('collab/dashboard.html')
