from flask import render_template, session, redirect, url_for, request, jsonify, abort
from . import blueprint
from .models import WTRoom, WTUser, WTSetting
from .database import db_session
from .auth import admin_required

@blueprint.before_request
def check_maintenance():
    # Bỏ qua các đường dẫn API Đăng nhập/Đăng ký để Admin vẫn có thể vào tắt Mode
    # hoặc bỏ qua static
    if request.path.startswith('/watchtogether/api/login') or request.path.startswith('/watchtogether/api/logout'):
        return None
        
    maintenance = db_session.query(WTSetting).filter_by(key='maintenance_mode').first()
    if maintenance and maintenance.value == '1':
        user = get_current_user()
        if not user or not getattr(user, 'is_admin', False):
            if request.path.startswith('/watchtogether/api/'):
                return jsonify({'error': 'Hệ thống đang bảo trì'}), 503
            return "Hệ thống đang bảo trì. Vui lòng quay lại sau.", 503

def get_current_user():
    user_id = session.get('wt_user_id')
    if not user_id: 
        return None
    return WTUser.query.get(user_id)

@blueprint.route('/')
def index():
    user = get_current_user()
    if user:
        rooms = WTRoom.query.filter(
            (WTRoom.is_public == True) | (WTRoom.host_id == user.id)
        ).order_by(WTRoom.last_updated.desc()).limit(15).all()
    else:
        rooms = WTRoom.query.filter_by(is_public=True).order_by(WTRoom.last_updated.desc()).limit(15).all()
    
    for r in rooms:
        host = WTUser.query.get(r.host_id)
        r.host_username = host.username if host else "Unknown"
        
    return render_template('watchtogether/dashboard.html', user=user, rooms=rooms)

@blueprint.route('/login')
def login():
    user = get_current_user()
    if user:
        return redirect(url_for('watchtogether.index'))
    return render_template('watchtogether/login.html')

@blueprint.route('/register')
def register():
    user = get_current_user()
    if user:
        return redirect(url_for('watchtogether.index'))
    return render_template('watchtogether/register.html')

@blueprint.route('/api/rooms', methods=['POST'])
def create_room():
    user = get_current_user()
    if not user: 
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json or {}
    video_id = data.get('video_id', 'dQw4w9WgXcQ')
    
    # Auto-fetch title via oEmbed if name is missing
    room_name = data.get('name', '').strip()
    if not room_name:
        import requests
        try:
            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            res = requests.get(oembed_url, timeout=3)
            if res.status_code == 200:
                room_name = res.json().get('title', '')
        except:
            pass
            
    if not room_name:
        room_name = f"Phòng của {user.username}"
        
    allow_guest_control = data.get('allow_guest_control', False) 
    password = data.get('password', '').strip()
    is_public = data.get('is_public', True)
    
    room = WTRoom(
        name=room_name, 
        host_id=user.id, 
        current_video_id=video_id, 
        allow_guest_control=allow_guest_control,
        password=password if password else None,
        is_public=is_public
    )
    db_session.add(room)
    db_session.commit()
    
    return jsonify({'success': True, 'room_id': room.id})

@blueprint.route('/api/room/<room_id>/update', methods=['POST'])
def update_room(room_id):
    user = get_current_user()
    if not user: 
        return jsonify({'error': 'Unauthorized'}), 401
        
    room = WTRoom.query.get(room_id)
    if not room or room.host_id != user.id:
        return jsonify({'error': 'Forbidden'}), 403
        
    data = request.json or {}
    
    if 'name' in data:
        new_name = data['name'].strip()
        if new_name:
            room.name = new_name
            
    if 'password' in data:
        room.password = data['password'].strip() or None
        
    if 'is_public' in data:
        room.is_public = bool(data['is_public'])
        
    if 'allow_guest_control' in data:
        room.allow_guest_control = bool(data['allow_guest_control'])
        
    db_session.commit()
    return jsonify({'success': True})

@blueprint.route('/room/<room_id>')
def room_view(room_id):
    user = get_current_user()
        
    room = WTRoom.query.get(room_id)
    if not room:
        return "Phòng không tồn tại", 404
        
    is_host = user and (user.id == room.host_id)
        
    if room.password and not is_host:
        unlocked = session.get(f'wt_unlocked_{room_id}', False)
        if not unlocked:
            return render_template('watchtogether/room_password.html', room=room)
        
    host = WTUser.query.get(room.host_id)
    return render_template('watchtogether/room.html', 
                             user=user, 
                             room=room, 
                             host=host,
                             is_host=is_host)

@blueprint.route('/api/room/<room_id>/unlock', methods=['POST'])
def unlock_room(room_id):
    room = WTRoom.query.get(room_id)
    if not room: return jsonify({'success': False, 'message': 'Không tìm thấy phòng'}), 404
    
    password = request.json.get('password', '')
    if room.password == password:
        session[f'wt_unlocked_{room_id}'] = True
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Mật khẩu không chính xác'}), 403

@blueprint.route('/admin')
@admin_required
def admin_dashboard():
    maintenance = db_session.query(WTSetting).filter_by(key='maintenance_mode').first()
    is_maintenance = (maintenance.value == '1') if maintenance else False
    users = WTUser.query.order_by(WTUser.created_at.desc()).all()
    return render_template('watchtogether/admin.html', user=get_current_user(), users=users, is_maintenance=is_maintenance)

@blueprint.route('/profile')
def profile_view():
    user = get_current_user()
    if not user:
        return redirect(url_for('watchtogether.login'))
        
    from .models import WTMembership
    rooms_joined = db_session.query(WTMembership).filter_by(user_id=user.id).count()
    return render_template('watchtogether/profile.html', user=user, rooms_joined=rooms_joined)

@blueprint.route('/api/profile/update', methods=['POST'])
def profile_update():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json or {}
    new_username = data.get('username', '').strip()
    new_password = data.get('password', '').strip()
    
    if new_username and new_username != user.username:
        existing = WTUser.query.filter_by(username=new_username).first()
        if existing:
            return jsonify({'success': False, 'message': 'Tên đăng nhập đã tồn tại'})
        user.username = new_username
        session['wt_username'] = new_username
        
    if new_password:
        user.set_password(new_password)
        
    db_session.commit()
    return jsonify({'success': True})

@blueprint.route('/api/admin/toggle_maintenance', methods=['POST'])
@admin_required
def admin_toggle_maintenance():
    setting = db_session.query(WTSetting).filter_by(key='maintenance_mode').first()
    if not setting:
        setting = WTSetting(key='maintenance_mode', value='1')
        db_session.add(setting)
    else:
        setting.value = '0' if setting.value == '1' else '1'
    db_session.commit()
    return jsonify({'success': True, 'maintenance_mode': setting.value == '1'})

@blueprint.route('/api/admin/delete_user', methods=['POST'])
@admin_required
def admin_delete_user():
    user_id = request.json.get('user_id')
    u = WTUser.query.get(user_id)
    if not u: return jsonify({'error': 'User not found'}), 404
    if u.is_admin: return jsonify({'error': 'Cannot delete an admin'}), 400
    db_session.delete(u)
    db_session.commit()
    return jsonify({'success': True})
