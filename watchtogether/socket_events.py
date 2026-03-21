from flask_socketio import SocketIO, join_room, leave_room, emit
from .database import db_session
from .models import WTRoom

socketio = SocketIO(cors_allowed_origins="*", async_mode='threading', path='/watchtogether/socket.io')

def init_sockets(app):
    socketio.init_app(app)

@socketio.on('join', namespace='/watchtogether')
def on_join(data):
    room_id = data.get('room_id')
    username = data.get('username')
    
    if not room_id or not username:
        return
        
    join_room(room_id)
    emit('system_message', {'msg': f'{username} đã tham gia phòng.'}, to=room_id)
    emit('request_sync_from_host', {}, to=room_id, include_self=False)

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
    if room and is_host:
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
    if room_id and message:
        emit('chat_message', {'username': username, 'message': message}, to=room_id)
