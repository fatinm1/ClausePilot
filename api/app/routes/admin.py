from app.security import require_auth, require_admin
import logging
from flask import Blueprint, request, jsonify, current_app
from app import db
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/users', methods=['GET'])
@require_admin
def list_users(user):
    User = current_app.User
    users = User.query.all()
    
    return jsonify({
        'users': [user.to_dict() for user in users]
    })

@admin_bp.route('/users', methods=['POST'])
@require_admin
def create_user(user):
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    User = current_app.User
    
    # Check if user already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 409
    
    # Create new user
    new_user = User(email=data['email'])
    new_user.set_password(data['password'])
    new_user.role = data.get('role', 'USER')
    new_user.is_active = data.get('is_active', True)
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({
        'message': 'User created successfully',
        'user': new_user.to_dict()
    }), 201

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@require_admin
def update_user(user, user_id):
    data = request.get_json()
    
    User = current_app.User
    target_user = User.query.get(user_id)
    
    if not target_user:
        return jsonify({'error': 'User not found'}), 404
    
    # Update fields
    if 'email' in data:
        target_user.email = data['email']
    if 'role' in data:
        target_user.role = data['role']
    if 'is_active' in data:
        target_user.is_active = data['is_active']
    
    db.session.commit()
    
    return jsonify({
        'message': 'User updated successfully',
        'user': target_user.to_dict()
    })

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@require_admin
def delete_user(user, user_id):
    User = current_app.User
    target_user = User.query.get(user_id)
    
    if not target_user:
        return jsonify({'error': 'User not found'}), 404
    
    # Prevent admin from deleting themselves
    if target_user.id == user.id:
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    db.session.delete(target_user)
    db.session.commit()
    
    return jsonify({'message': 'User deleted successfully'})

@admin_bp.route('/dashboard', methods=['GET'])
@require_admin
def admin_dashboard(user):
    User = current_app.User
    Document = current_app.Document
    ProcessingRule = current_app.ProcessingRule
    
    # Get system statistics
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_documents = Document.query.count()
    total_rules = ProcessingRule.query.count()
    
    # Get recent activity
    recent_documents = Document.query.order_by(Document.uploaded_at.desc()).limit(5).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    return jsonify({
        'statistics': {
            'total_users': total_users,
            'active_users': active_users,
            'total_documents': total_documents,
            'total_rules': total_rules
        },
        'recent_activity': {
            'documents': [doc.to_dict() for doc in recent_documents],
            'users': [user.to_dict() for user in recent_users]
        }
    })

@admin_bp.route('/create-admin', methods=['POST'])
@require_admin
def create_admin(user):
    """Create the first admin user (no authentication required)"""
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400
    
    User = current_app.User
    
    # Check if any admin already exists
    existing_admin = User.query.filter_by(role='ADMIN').first()
    if existing_admin:
        return jsonify({'error': 'Admin user already exists'}), 409
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=data['email']).first()
    if existing_user:
        return jsonify({'error': 'Email already registered'}), 409
    
    # Create admin user
    admin_user = User(email=data['email'])
    admin_user.set_password(data['password'])
    admin_user.role = 'ADMIN'
    admin_user.is_active = True
    
    try:
        db.session.add(admin_user)
        db.session.commit()
        
        return jsonify({
            'message': 'Admin user created successfully',
            'user': admin_user.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create admin: {str(e)}'}), 500

@admin_bp.route('/system-health', methods=['GET'])
@require_admin
def system_health(user):
    """Check system health status"""
    import os
    import psutil
    
    # Database health check
    try:
        db.session.execute('SELECT 1')
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'
    
    # File system health check
    upload_dir = 'uploads'
    output_dir = 'outputs'
    
    upload_exists = os.path.exists(upload_dir)
    output_exists = os.path.exists(output_dir)
    
    # Disk usage
    try:
        disk_usage = psutil.disk_usage('/')
        disk_percent = disk_usage.percent
    except:
        disk_percent = 'unknown'
    
    return jsonify({
        'status': 'healthy',
        'database': db_status,
        'file_system': {
            'uploads_directory': upload_exists,
            'outputs_directory': output_exists
        },
        'disk_usage': f'{disk_percent}%' if isinstance(disk_percent, (int, float)) else disk_percent
    })
