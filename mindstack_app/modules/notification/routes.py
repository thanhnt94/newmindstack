from flask import render_template, jsonify, request, current_app
from flask_login import login_required, current_user
from . import notification_bp
from .services import NotificationService
from .models import PushSubscription
from ...db_instance import db

@notification_bp.route('/api/list')
@login_required
def api_get_notifications():
    limit = request.args.get('limit', 20, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    notifs = NotificationService.get_user_notifications(current_user.user_id, limit, offset)
    unread_count = NotificationService.get_unread_count(current_user.user_id)
    
    return jsonify({
        'notifications': [n.to_dict() for n in notifs],
        'unread_count': unread_count
    })

@notification_bp.route('/api/mark-read/<int:notif_id>', methods=['POST'])
@login_required
def api_mark_read(notif_id):
    success = NotificationService.mark_as_read(notif_id, current_user.user_id)
    return jsonify({'success': success})

@notification_bp.route('/api/mark-all-read', methods=['POST'])
@login_required
def api_mark_all_read():
    NotificationService.mark_all_as_read(current_user.user_id)
    return jsonify({'success': True})

@notification_bp.route('/api/subscribe', methods=['POST'])
@login_required
def api_subscribe():
    data = request.json
    if not data or not data.get('endpoint'):
        return jsonify({'error': 'Invalid data'}), 400

    endpoint = data['endpoint']
    keys = data.get('keys', {})
    auth = keys.get('auth')
    p256dh = keys.get('p256dh')
    
    # Check if exists
    sub = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if not sub:
        sub = PushSubscription(
            user_id=current_user.user_id,
            endpoint=endpoint,
            auth_key=auth,
            p256dh_key=p256dh
        )
        db.session.add(sub)
    else:
        # Update user/keys if changed
        sub.user_id = current_user.user_id
        sub.auth_key = auth
        sub.p256dh_key = p256dh
        
    db.session.commit()
    return jsonify({'success': True})

@notification_bp.route('/api/vapid-public-key')
def api_vapid_key():
    from ...services.config_service import get_runtime_config
    # Usually VAPID keys are in config, assuming key name 'VAPID_PUBLIC_KEY'
    # Fallback to empty if not set
    pub_key = get_runtime_config('VAPID_PUBLIC_KEY', current_app.config.get('VAPID_PUBLIC_KEY'))
    return jsonify({'publicKey': pub_key})

@notification_bp.route('/sw.js')
def service_worker():
    from flask import send_from_directory, current_app
    import os
    # Serve from the module folder
    module_dir = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(module_dir, 'pro_sw.js')
