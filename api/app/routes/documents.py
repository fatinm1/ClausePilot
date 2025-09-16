import os
import sys
import json
import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, send_file
from werkzeug.utils import secure_filename
from functools import wraps
import uuid
from app import db

logger = logging.getLogger(__name__)
documents_bp = Blueprint('documents', __name__)

# File upload configuration
ALLOWED_EXTENSIONS = {'docx'}
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def require_auth(f):
    """Decorator to require authentication"""
    def decorated_function(*args, **kwargs):
        # For demo purposes, create a mock user based on X-User-ID header
        user_id = request.headers.get('X-User-ID', '1')
        if user_id == '1':
            # Mock admin user
            class MockUser:
                id = 1
                role = 'ADMIN'
            user = MockUser()
        elif user_id == '2':
            # Mock regular user
            class MockUser:
                id = 2
                role = 'USER'
            user = MockUser()
        else:
            return jsonify({'error': 'Unauthorized'}), 401
        
        return f(user, *args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # For demo purposes, check if user is admin
        if user_id == '1':
            user = type('MockUser', (), {'id': 1, 'role': 'admin'})()
        else:
            # For non-demo users, check against database
            User = current_app.User
            user = User.query.get(user_id)
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            if not user.is_admin():
                return jsonify({'error': 'Admin access required'}), 403
        
        return f(user, *args, **kwargs)
    return decorated_function

@documents_bp.route('/upload', methods=['POST'])
@require_auth
def upload_document(user):
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file:
        return jsonify({'error': 'Invalid file'}), 400
    
    # Check file size before processing
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning
    
    # Check if file is too large (50MB limit)
    max_size = 50 * 1024 * 1024  # 50MB
    if file_size > max_size:
        return jsonify({
            'error': 'File too large',
            'message': f'File size ({file_size} bytes) exceeds the maximum allowed limit of 50MB',
            'max_size': '50MB',
            'current_size': f'{file_size} bytes'
        }), 413
    
    # Generate unique filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{timestamp}_{unique_id}_{secure_filename(file.filename)}"
    
    # Ensure uploads directory exists
    upload_dir = 'uploads'
    os.makedirs(upload_dir, exist_ok=True)
    
    # Use absolute path to avoid issues in Railway
    file_path = os.path.abspath(os.path.join(upload_dir, filename))
    
    # Save file with proper error handling
    try:
        file.save(file_path)
        
        # Verify file was saved correctly
        if not os.path.exists(file_path):
            raise Exception("File was not saved successfully")
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Validate file size matches what we expect
        if file_size == 0:
            raise Exception("Uploaded file is empty")
        
        # Log file details for debugging
        logger.info(f"File uploaded successfully: {filename}, size: {file_size} bytes")
        
    except Exception as e:
        logger.error(f"Error saving file: {str(e)}")
        return jsonify({'error': f'Failed to save file: {str(e)}'}), 500
    
    # Create document record
    Document = current_app.Document
    document = Document(
        user_id=user.id,
        filename=filename,
        original_filename=secure_filename(file.filename),
        file_path=file_path,
        file_size=file_size,
        status='uploaded'
    )
    
    db.session.add(document)
    db.session.commit()
    
    return jsonify({
        'message': 'Document uploaded successfully',
        'document': document.to_dict()
    }), 201

@documents_bp.route('/<int:document_id>/process', methods=['POST'])
@require_auth
def process_document(user, document_id):
    Document = current_app.Document
    document = Document.query.get(document_id)
    
    if not document:
        return jsonify({'error': 'Document not found'}), 404
    
    if document.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get request data for custom rules, firm details, and signature
    data = request.get_json() or {}
    custom_rules = data.get('custom_rules', [])
    firm_details = data.get('firm_details', {})
    signature_path = data.get('signature_path')
    
    # Update status to processing
    document.status = 'processing'
    db.session.commit()
    
    try:
        # Validate file exists and is readable
        if not os.path.exists(document.file_path):
            raise Exception(f"Document file not found: {document.file_path}")
        
        # Check file size
        file_size = os.path.getsize(document.file_path)
        if file_size == 0:
            raise Exception("Document file is empty")
        
        # Log file size for monitoring
        logger.info(f"Processing document: {file_size} bytes ({file_size/1024:.1f} KB)")
        
        # Validate file is a valid .docx file
        try:
            from docx import Document as DocxDocument
            # Try to open the document to validate it's a proper .docx file
            test_doc = DocxDocument(document.file_path)
            # If we get here, the file is valid
            test_doc = None  # Close the test document
            logger.info(f"Document validation successful: {document.file_path}")
        except Exception as e:
            logger.error(f"Document validation failed: {str(e)}")
            logger.error(f"File path: {document.file_path}")
            logger.error(f"File exists: {os.path.exists(document.file_path)}")
            logger.error(f"File size: {os.path.getsize(document.file_path) if os.path.exists(document.file_path) else 'N/A'}")
            raise Exception(f"Invalid .docx file: {str(e)}")
        
        # Import AI service
        from app.services.ai_redlining import AIRedliningService, DocumentProcessor
        
        # Initialize AI service
        logger.warning("Initializing AI service for document processing...")
        logger.warning(f"Current working directory: {os.getcwd()}")
        logger.warning(f"Python path: {sys.path[:3]}...")
        
        try:
            # Check environment variables before creating AI service
            api_key = os.getenv('OPENAI_API_KEY')
            logger.warning(f"OPENAI_API_KEY available: {bool(api_key)}")
            logger.warning(f"OPENAI_API_KEY length: {len(api_key) if api_key else 0}")
            logger.warning(f"OPENAI_API_KEY starts with: {api_key[:10] if api_key and len(api_key) > 10 else 'N/A'}")
            
            ai_service = AIRedliningService()
            logger.warning(f"AI service initialized - Client available: {ai_service.client is not None}")
            logger.warning(f"AI service model: {ai_service.model}")
            if ai_service.client is None:
                logger.warning("AI service client is None - will use mock mode")
            else:
                logger.warning("AI service client is available - will use real OpenAI API")
        except Exception as e:
            logger.error(f"Error creating AI service: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return jsonify({"error": f"Error initializing AI service: {str(e)}"}), 500
        
        # Process document with AI and apply modifications
        # The DocumentProcessor now handles large files automatically
        logger.warning("Creating DocumentProcessor with AI service")
        logger.warning(f"AI service client available: {ai_service.client is not None}")
        logger.warning(f"AI service model: {ai_service.model}")
        
        processor = DocumentProcessor(ai_service)
        logger.warning("DocumentProcessor created successfully")
        
        logger.warning("Starting document processing...")
        result = processor.process_document(document.file_path, custom_rules, firm_details, signature_path)
        logger.warning(f"Document processing completed. Result: {result}")
        
        if not result.get('success'):
            raise Exception(result.get('error', 'Document processing failed'))
        
        # Get the output path from the processor
        output_path = result.get('output_path')
        
        # Update document status
        document.status = 'completed'
        document.processed_at = datetime.utcnow()
        document.output_path = output_path
        db.session.commit()
        
        return jsonify({
            'message': 'Document processed successfully',
            'result': result,
            'document': document.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        document.status = 'error'
        document.error_message = str(e)
        db.session.commit()
        
        return jsonify({
            'error': f'Error processing document: {str(e)}'
        }), 500

@documents_bp.route('/<int:document_id>/download')
@require_auth
def download_document(user, document_id):
    Document = current_app.Document
    document = Document.query.get(document_id)
    
    if not document:
        return jsonify({'error': 'Document not found'}), 404
    
    if document.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    if not document.output_path or not os.path.exists(document.output_path):
        return jsonify({'error': 'No processed document available for download'}), 404
    
    from flask import send_file
    return send_file(
        document.output_path,
        as_attachment=True,
        download_name=f"processed_{document.original_filename}"
    )

@documents_bp.route('/', methods=['GET'])
@require_auth
def list_documents(user):
    Document = current_app.Document
    documents = Document.query.filter_by(user_id=user.id).order_by(Document.uploaded_at.desc()).all()
    
    return jsonify({
        'documents': [doc.to_dict() for doc in documents]
    })

@documents_bp.route('/<int:document_id>', methods=['GET'])
@require_auth
def get_document(user, document_id):
    Document = current_app.Document
    document = Document.query.get(document_id)
    
    if not document:
        return jsonify({'error': 'Document not found'}), 404
    
    if document.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Add processing progress information for large files
    document_dict = document.to_dict()
    
    if document.status == 'processing':
        # Estimate processing time based on file size
        file_size_kb = document.file_size / 1024 if document.file_size else 0
        if file_size_kb > 100:
            document_dict['processing_info'] = {
                'estimated_time': f"{max(30, int(file_size_kb / 10))} seconds",
                'file_size_kb': round(file_size_kb, 1),
                'status_message': 'Processing large document - this may take a few minutes'
            }
        else:
            document_dict['processing_info'] = {
                'estimated_time': '10-30 seconds',
                'file_size_kb': round(file_size_kb, 1),
                'status_message': 'Processing document'
            }
    
    return jsonify({
        'document': document_dict
    })

@documents_bp.route('/<int:document_id>', methods=['DELETE'])
@require_auth
def delete_document(user, document_id):
    Document = current_app.Document
    document = Document.query.get(document_id)
    
    if not document:
        return jsonify({'error': 'Document not found'}), 404
    
    if document.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Delete file from filesystem
    if os.path.exists(document.file_path):
        os.remove(document.file_path)
    
    if document.output_path and os.path.exists(document.output_path):
        os.remove(document.output_path)
    
    # Delete from database
    db.session.delete(document)
    db.session.commit()
    
    return jsonify({'message': 'Document deleted successfully'})
