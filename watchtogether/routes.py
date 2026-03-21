from flask import render_template, session, redirect, url_for, request, jsonify
from . import blueprint
from .models import WTRoom, WTUser
from .database import db_session

def get_current_user():
    user_id = session.get('wt_user_id')
    if not user_id: 
        return None
    return WTUser.query.get(user_id)

@blueprint.route('/')
def index():
    user = get_current_user()
    if not user:
        return render_template('watchtogether/login.html')
    rooms = WTRoom.query.order_by(WTRoom.last_updated.desc()).limit(15).all()
    
    for r in rooms:
        host = WTUser.query.get(r.host_id)
        r.host_username = host.username if host else "Unknown"
        
    return render_template('watchtogether/dashboard.html', user=user, rooms=rooms)

@blueprint.route('/api/rooms', methods=['POST'])
def create_room():
    user = get_current_user()
    if not user: 
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json or {}
    room_name = data.get('name', f"Phòng của {user.username}")
    video_id = data.get('video_id', 'dQw4w9WgXcQ') 
    
    room = WTRoom(name=room_name, host_id=user.id, current_video_id=video_id)
    db_session.add(room)
    db_session.commit()
    
    return jsonify({'success': True, 'room_id': room.id})

@blueprint.route('/room/<room_id>')
def room_view(room_id):
    user = get_current_user()
    if not user:
        return render_template('watchtogether/login.html', room_id=room_id)
        
    room = WTRoom.query.get(room_id)
    if not room:
        return "Phòng không tồn tại", 404
        
    host = WTUser.query.get(room.host_id)
    return render_template('watchtogether/room.html', 
                             user=user, 
                             room=room, 
                             host=host,
                             is_host=(user.id == room.host_id))
