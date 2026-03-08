from flask import render_template, request, abort, current_app, redirect, url_for, Blueprint
from mindstack_app.utils.template_helpers import render_dynamic_template
from flask_login import login_required, current_user
from .. import blueprint

@blueprint.route('/')
@login_required
def index():
    """Kanji lookup and learning page."""
    return render_dynamic_template('modules/kanji/index.html')
