from app.security import require_auth
from flask import Blueprint, request, jsonify, make_response, current_app
from app import db
import jwt
import datetime
from functools import wraps

auth_bp = Blueprint('auth', __name__)

def create_tokens(user_id):
    secret_key = current_app.config.get('JWT_SECRET_KEY', 'fallback-secret-key')
    access_token = jwt.encode(
        {'user_id': user_id, 'type': 'access', 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)},
        secret_key,
        algorithm='HS256'
    )
    refresh_token = jwt.encode(
        {'user_id': user_id, 'type': 'refresh', 'exp': datetime.datetime.utcnow() + datetime.timedelta(days=30)},
        secret_key,
        algorithm='HS256'
    )
    return access_token, refresh_token

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    User = current_app.User
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 409
    
    # Create user with basic info
    user = User(email=data['email'])
    user.set_password(data['password'])
    
    # Set role to USER by default (first user can be manually made admin)
    user.role = 'USER'
    user.is_active = True
    
    db.session.add(user)
    db.session.commit()
    
    access_token, refresh_token = create_tokens(user.id)
    
    response = make_response(jsonify({
        'message': 'User registered successfully',
        'user': user.to_dict()
    }))
    response.set_cookie('access_token', access_token, httponly=True, secure=current_app.config.get('SESSION_COOKIE_SECURE', False), samesite='Lax')
    response.set_cookie('refresh_token', refresh_token, httponly=True, secure=current_app.config.get('SESSION_COOKIE_SECURE', False), samesite='Lax')
    
    return response, 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    User = current_app.User
    user = User.query.filter_by(email=data['email']).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if not user.is_active:
        return jsonify({'error': 'Account is deactivated'}), 401
    
    access_token, refresh_token = create_tokens(user.id)
    
    response = make_response(jsonify({
        'message': 'Login successful', 
        'user': user.to_dict()
    }))
    response.set_cookie('access_token', access_token, httponly=True, secure=current_app.config.get('SESSION_COOKIE_SECURE', False), samesite='Lax')
    response.set_cookie('refresh_token', refresh_token, httponly=True, secure=current_app.config.get('SESSION_COOKIE_SECURE', False), samesite='Lax')
    
    return response

@auth_bp.route('/logout', methods=['POST'])
def logout():
    response = make_response(jsonify({'message': 'Logged out successfully'}))
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    return response

@auth_bp.route('/refresh', methods=['POST'])
def refresh():
    refresh_token = request.cookies.get('refresh_token')
    
    if not refresh_token:
        return jsonify({'error': 'Refresh token required'}), 401
    
    try:
        secret_key = current_app.config.get('JWT_SECRET_KEY', 'fallback-secret-key')
        payload = jwt.decode(refresh_token, secret_key, algorithms=['HS256'], options={'require': ['exp', 'user_id', 'type']})
        if payload['type'] != 'refresh':
            raise jwt.InvalidTokenError('Wrong token type')
        user = db.session.get(current_app.User, payload['user_id'])
        if not user or not user.is_active:
            raise jwt.InvalidTokenError('Inactive account')
        user_id = payload['user_id']
        
        access_token, new_refresh_token = create_tokens(user_id)
        
        response = make_response(jsonify({'message': 'Token refreshed'}))
        response.set_cookie('access_token', access_token, httponly=True, secure=current_app.config.get('SESSION_COOKIE_SECURE', False), samesite='Lax')
        response.set_cookie('refresh_token', new_refresh_token, httponly=True, secure=current_app.config.get('SESSION_COOKIE_SECURE', False), samesite='Lax')
        
        return response
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Refresh token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid refresh token'}), 401

@auth_bp.route('/me', methods=['GET'])
@require_auth
def me(user):
    return jsonify({'user': user.to_dict()})
