"""Blueprint registration for the goals module."""

from flask import Blueprint


goals_bp = Blueprint('goals', __name__, template_folder='templates')

from . import routes  # noqa: E402  # isort:skip
