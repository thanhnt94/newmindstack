# mindstack_app/modules/session_hub/routes/views.py
from flask import request, abort
from flask_login import login_required, current_user
from mindstack_app.utils.template_helpers import render_dynamic_template
from ..services.hub_service import SessionHubService
from .. import session_hub_bp


@session_hub_bp.route('/<int:session_id>/summary')
@login_required
def session_summary_hub(session_id):
    """Session Summary Hub page — aggregated view of a completed session."""
    page = request.args.get('page', 1, type=int)

    data = SessionHubService.get_summary_data(
        user_id=current_user.user_id,
        session_id=session_id,
        page=page
    )

    if data is None:
        abort(404, description="Session not found")

    # Build a simple pagination object for template iteration
    class PaginationWrapper:
        def __init__(self, pag_data):
            self.items = pag_data['items']
            self.total = pag_data['total']
            self.pages = pag_data['pages']
            self.page = pag_data['page']
            self.per_page = pag_data['per_page']
            self.has_prev = pag_data['has_prev']
            self.has_next = pag_data['has_next']
            self.prev_num = pag_data['prev_num']
            self.next_num = pag_data['next_num']

        def iter_pages(self, left_edge=2, left_current=2, right_current=5, right_edge=2):
            last = 0
            for num in range(1, self.pages + 1):
                if num <= left_edge or \
                   (num > self.page - left_current - 1 and num < self.page + right_current) or \
                   num > self.pages - right_edge:
                    if last + 1 != num:
                        yield None
                    yield num
                    last = num

    pagination = PaginationWrapper(data['pagination'])

    return render_dynamic_template(
        'modules/session_hub/summary.html',
        summary=data['summary'],
        set_id=data['set_id'],
        pagination=pagination,
        logs=data['logs']
    )
