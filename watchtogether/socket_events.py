from flask_socketio import SocketIO, join_room, leave_room, emit
from .database import db_session
from .models import WTRoom

socketio = SocketIO(cors_allowed_origins="*", async_mode='threading', path='/watchtogether/socket.io')

# In-memory store for room presence
# Format: { room_id: { sid: {'username': '...', 'is_member': True/False} } }
ROOM_PRESENCE = {}

def broadcast_presence(room_id):
    users = ROOM_PRESENCE.get(room_id, {})
    total = len(users)
    members = sum(1 for u in users.values() if u['is_member'])
    guests = total - members
    socketio.emit('presence_update', {'total': total, 'members': members, 'guests': guests}, to=room_id, namespace='/watchtogether')

def init_sockets(app):
    socketio.init_app(app)

@socketio.on('join', namespace='/watchtogether')
def on_join(data):
    room_id = data.get('room_id')
    username = data.get('username')
    user_id = data.get('user_id')
    
    if not room_id or not username:
        return
        
    join_room(room_id)
    emit('system_message', {'msg': f'{username} đã tham gia phòng.'}, to=room_id)
    emit('request_sync_from_host', {}, to=room_id, include_self=False)
    
    # Load history
    from .models import WTChatMessage, WTVideoHistory
    from .database import db_session
    
    try:
        chat_history = db_session.query(WTChatMessage).filter_by(room_id=room_id).order_by(WTChatMessage.created_at.desc()).limit(50).all()
        chat_data = [{
            'username': msg.username, 
            'message': msg.message, 
            'video_id': msg.video_id, 
            'timestamp': msg.timestamp,
            'created_at': msg.created_at.isoformat() + 'Z' if msg.created_at else None
        } for msg in reversed(chat_history)]
        emit('chat_history', chat_data)
        
        video_history = db_session.query(WTVideoHistory).filter_by(room_id=room_id).order_by(WTVideoHistory.added_at.desc()).limit(10).all()
        video_data = [{'video_id': v.video_id, 'added_at': v.added_at.strftime('%H:%M')} for v in video_history]
        emit('video_history', video_data)
    except Exception as e:
        print(f"Error loading history: {e}")
    
    # Track membership
    if user_id:
        from .models import WTMembership
        from datetime import datetime, timezone
        from .database import db_session
        existing = db_session.query(WTMembership).filter_by(user_id=user_id, room_id=room_id).first()
        if not existing:
            try:
                mem = WTMembership(user_id=user_id, room_id=room_id)
                db_session.add(mem)
                db_session.commit()
            except:
                db_session.rollback()

    # Track online presence
    from flask import request
    if room_id not in ROOM_PRESENCE:
        ROOM_PRESENCE[room_id] = {}
    ROOM_PRESENCE[room_id][request.sid] = {
        'username': username,
        'is_member': user_id is not None
    }
    broadcast_presence(room_id)

@socketio.on('disconnect', namespace='/watchtogether')
def on_disconnect():
    from flask import request
    for room_id, users in ROOM_PRESENCE.items():
        if request.sid in users:
            del users[request.sid]
            broadcast_presence(room_id)
            break

@socketio.on('watch_heartbeat', namespace='/watchtogether')
def on_watch_heartbeat(data):
    user_id = data.get('user_id')
    if user_id:
        from .models import WTUser
        from .database import db_session
        user = db_session.query(WTUser).get(user_id)
        if user:
            user.total_watch_minutes = (user.total_watch_minutes or 0) + 1
            try:
                db_session.commit()
            except:
                db_session.rollback()

@socketio.on('change_video', namespace='/watchtogether')
def on_change_video(data):
    room_id = data.get('room_id')
    new_video_id = data.get('video_id')
    start_time = data.get('start_time', 0)
    is_host = data.get('is_host', False)
    
    if not room_id or not new_video_id:
        return
        
    from .models import WTVideoHistory
    room = WTRoom.query.get(room_id)
    if room and (is_host or room.allow_guest_control):
        room.current_video_id = new_video_id
        room.current_time = start_time
        room.is_playing = True
        
        hist = WTVideoHistory(room_id=room_id, video_id=new_video_id)
        db_session.add(hist)
        
        try:
            db_session.commit()
            emit('video_changed', {'video_id': new_video_id, 'start_time': start_time}, to=room_id)
            emit('system_message', {'msg': 'Danh sách đã chuyển sang Video mới!'}, to=room_id)
        except Exception as e:
            db_session.rollback()
            print(f"Error changing video: {e}")

@socketio.on('sync_state', namespace='/watchtogether')
def on_sync_state(data):
    room_id = data.get('room_id')
    state = data.get('state') 
    time = data.get('time')
    video_id = data.get('video_id')
    is_host = data.get('is_host', False)
    
    if not room_id:
        return

    room = WTRoom.query.get(room_id)
    if not room: return
    
    can_control = is_host or room.allow_guest_control
    
    if can_control:
        if video_id: room.current_video_id = video_id
        if state: room.is_playing = (state == 'playing')
        if time is not None: room.current_time = int(time)
        try:
            db_session.commit()
        except:
            db_session.rollback()
            
        emit('receive_state', data, to=room_id, include_self=False)

@socketio.on('chat_message', namespace='/watchtogether')
def on_chat_message(data):
    room_id = data.get('room_id')
    username = data.get('username', 'Khách')
    message = data.get('message', '')
    video_id = data.get('video_id')
    timestamp = data.get('timestamp')
    if room_id and message:
        from .models import WTChatMessage
        from .database import db_session
        try:
            msg = WTChatMessage(room_id=room_id, username=username, message=message, video_id=video_id, timestamp=timestamp)
            db_session.add(msg)
            db_session.commit()
        except Exception as e:
            db_session.rollback()
            print(f"Error saving chat: {e}")

        emit('chat_message', {
            'username': username, 
            'message': message,
            'video_id': video_id,
            'timestamp': timestamp
        }, to=room_id)
