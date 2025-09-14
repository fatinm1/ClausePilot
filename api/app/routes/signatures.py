from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from functools import wraps
import os
import uuid
from datetime import datetime

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get user ID from header
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return jsonify({'error': 'User ID required'}), 401
        
        # Create a mock user object for compatibility
        class MockUser:
            def __init__(self, user_id):
                self.id = int(user_id)
                self.role = 'USER'  # Default role
        
        user = MockUser(user_id)
        return f(user, *args, **kwargs)
    return decorated_function

signatures_bp = Blueprint('signatures', __name__)

# Allowed signature file extensions
ALLOWED_SIGNATURE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}

def allowed_signature_file(filename):
    """Check if the uploaded file is an allowed signature format"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_SIGNATURE_EXTENSIONS

@signatures_bp.route('/upload', methods=['POST'])
@require_auth
def upload_signature(user):
    """Upload a signature image file"""
    try:
        # Check if signature file is present
        if 'signature' not in request.files:
            return jsonify({'error': 'No signature file provided'}), 400
        
        signature_file = request.files['signature']
        
        # Check if file is selected
        if signature_file.filename == '':
            return jsonify({'error': 'No signature file selected'}), 400
        
        # Validate file type
        if not allowed_signature_file(signature_file.filename):
            return jsonify({
                'error': 'Invalid file type',
                'message': f'Allowed types: {", ".join(ALLOWED_SIGNATURE_EXTENSIONS)}'
            }), 400
        
        # Create signatures directory if it doesn't exist
        signatures_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'signatures')
        os.makedirs(signatures_dir, exist_ok=True)
        
        # Generate unique filename
        file_extension = signature_file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{user.id}_{uuid.uuid4().hex}.{file_extension}"
        secure_name = secure_filename(unique_filename)
        
        # Save signature file
        signature_path = os.path.join(signatures_dir, secure_name)
        signature_file.save(signature_path)
        
        # Get file size
        file_size = os.path.getsize(signature_path)
        
        # Log signature upload
        current_app.logger.info(f"Signature uploaded: {secure_name}, size: {file_size} bytes, user: {user.id}")
        
        return jsonify({
            'message': 'Signature uploaded successfully',
            'signature_path': signature_path,
            'filename': secure_name,
            'file_size': file_size
        }), 201
        
    except Exception as e:
        current_app.logger.error(f"Error uploading signature: {str(e)}")
        return jsonify({
            'error': f'Failed to upload signature: {str(e)}'
        }), 500

@signatures_bp.route('/<signature_filename>', methods=['GET'])
@require_auth
def get_signature(user, signature_filename):
    """Get a signature image file"""
    try:
        # Validate filename format (should be user_id_uuid.extension)
        if not signature_filename.startswith(f"{user.id}_"):
            return jsonify({'error': 'Unauthorized access to signature'}), 403
        
        signatures_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'signatures')
        signature_path = os.path.join(signatures_dir, signature_filename)
        
        # Check if file exists
        if not os.path.exists(signature_path):
            return jsonify({'error': 'Signature not found'}), 404
        
        # Return file
        from flask import send_file
        return send_file(signature_path, as_attachment=False)
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving signature: {str(e)}")
        return jsonify({
            'error': f'Failed to retrieve signature: {str(e)}'
        }), 500

@signatures_bp.route('/<signature_filename>', methods=['DELETE'])
@require_auth
def delete_signature(user, signature_filename):
    """Delete a signature image file"""
    try:
        # Validate filename format (should be user_id_uuid.extension)
        if not signature_filename.startswith(f"{user.id}_"):
            return jsonify({'error': 'Unauthorized access to signature'}), 403
        
        signatures_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'signatures')
        signature_path = os.path.join(signatures_dir, signature_filename)
        
        # Check if file exists
        if not os.path.exists(signature_path):
            return jsonify({'error': 'Signature not found'}), 404
        
        # Delete file
        os.remove(signature_path)
        
        current_app.logger.info(f"Signature deleted: {signature_filename}, user: {user.id}")
        
        return jsonify({
            'message': 'Signature deleted successfully'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Error deleting signature: {str(e)}")
        return jsonify({
            'error': f'Failed to delete signature: {str(e)}'
        }), 500
