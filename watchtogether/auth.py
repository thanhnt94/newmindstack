from flask import request, session, jsonify
from . import blueprint
from .models import WTUser
from .database import db_session

@blueprint.route('/api/login', methods=['POST'])
def api_login():
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')
    user = WTUser.query.filter_by(username=username).first()
    
    if user and user.check_password(password):
        session['wt_user_id'] = user.id
        session['wt_username'] = user.username
        session.modified = True
        return jsonify({'success': True, 'username': user.username})
        
    return jsonify({'success': False, 'message': 'Sai tên đăng nhập hoặc mật khẩu'}), 401

@blueprint.route('/api/register', methods=['POST'])
def api_register():
    data = request.json or {}
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
         return jsonify({'success': False, 'message': 'Cần nhập đủ tài khoản và mật khẩu'}), 400
         
    if WTUser.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': 'Tên đăng nhập đã tồn tại'}), 400
    
    user = WTUser(username=username)
    user.set_password(password)
    db_session.add(user)
    db_session.commit()
    
    session['wt_user_id'] = user.id
    session['wt_username'] = user.username
    session.modified = True
    return jsonify({'success': True, 'username': user.username})

@blueprint.route('/api/logout', methods=['POST'])
def api_logout():
    session.pop('wt_user_id', None)
    session.pop('wt_username', None)
    session.modified = True
    return jsonify({'success': True})

@blueprint.route('/api/me', methods=['GET'])
def api_me():
    if 'wt_user_id' in session:
        return jsonify({'logged_in': True, 'username': session.get('wt_username'), 'user_id': session.get('wt_user_id')})
    return jsonify({'logged_in': False}), 401
