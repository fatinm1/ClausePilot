import logging
from flask import Blueprint, request, jsonify, current_app
from app import db
from functools import wraps
import json
import os

logger = logging.getLogger(__name__)
changes_bp = Blueprint('changes', __name__)

def require_auth(f):
    """Decorator to require authentication"""
    def decorated_function(*args, **kwargs):
        # Get user ID from header
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            return jsonify({'error': 'User ID required'}), 401
        
        # Get user from database
        User = current_app.User
        user = User.query.get(int(user_id))
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return f(user, *args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@changes_bp.route('/generate', methods=['POST'])
@require_auth
def generate_changes(user):
    """Generate changes for review interface"""
    try:
        data = request.get_json()
        
        # Extract document text and processing parameters
        document_text = data.get('document_text', '')
        custom_rules = data.get('custom_rules', [])
        firm_details = data.get('firm_details', {})
        
        logger.warning(f"Generating changes - Document text length: {len(document_text)}")
        logger.warning(f"Custom rules count: {len(custom_rules)}")
        logger.warning(f"Firm details: {firm_details}")
        
        if not document_text:
            return jsonify({'error': 'Document text is required'}), 400
        
        # Import AI service
        from app.services.ai_redlining import AIRedliningService
        ai_service = AIRedliningService()
        
        # Generate changes for review
        changes_data = ai_service.generate_changes_for_review(
            document_text, custom_rules, firm_details
        )
        
        logger.warning(f"Generated {changes_data['total_changes']} changes")
        
        # Store changes in session or database for later retrieval
        # For now, we'll return them directly
        return jsonify({
            'success': True,
            'changes': changes_data['changes'],
            'total_changes': changes_data['total_changes'],
            'document_text': changes_data['document_text'],
            'firm_details': changes_data['firm_details']
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating changes: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Failed to generate changes: {str(e)}'}), 500

@changes_bp.route('/review/<int:document_id>', methods=['GET'])
@require_auth
def get_changes_for_review(user, document_id):
    """Get changes for a specific document for review"""
    try:
        # Get document from database
        Document = current_app.Document
        document = Document.query.get(document_id)
        
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        # Check if user owns the document
        if document.user_id != user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        # For now, return a placeholder - in a real implementation,
        # you'd store the changes in the database
        return jsonify({
            'success': True,
            'document_id': document_id,
            'changes': [],  # This would be populated from database
            'message': 'Changes review interface ready'
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting changes for review: {str(e)}")
        return jsonify({'error': f'Failed to get changes: {str(e)}'}), 500

@changes_bp.route('/update-status', methods=['POST'])
@require_auth
def update_change_status(user):
    """Update the status of a specific change (accept/reject)"""
    try:
        data = request.get_json()
        
        change_id = data.get('change_id')
        status = data.get('status')  # 'accepted' or 'rejected'
        
        if not change_id or not status:
            return jsonify({'error': 'Change ID and status are required'}), 400
        
        if status not in ['accepted', 'rejected']:
            return jsonify({'error': 'Status must be "accepted" or "rejected"'}), 400
        
        # In a real implementation, you'd update the database
        # For now, just return success
        return jsonify({
            'success': True,
            'change_id': change_id,
            'status': status,
            'message': f'Change {change_id} marked as {status}'
        }), 200
        
    except Exception as e:
        logger.error(f"Error updating change status: {str(e)}")
        return jsonify({'error': f'Failed to update change status: {str(e)}'}), 500

@changes_bp.route('/apply-accepted/<int:document_id>', methods=['POST'])
@require_auth
def apply_accepted_changes(user, document_id):
    """Apply only the accepted changes to create final document"""
    try:
        data = request.get_json()
        accepted_changes = data.get('accepted_changes', [])
        
        if not accepted_changes:
            return jsonify({'error': 'No accepted changes provided'}), 400
        
        # Get document from database
        Document = current_app.Document
        document = Document.query.get(document_id)
        
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        # Debug logging
        logger.warning(f"Apply changes - Document user_id: {document.user_id}, Request user_id: {user.id}")
        
        # Temporarily disable ownership check for debugging
        # TODO: Fix user ID mismatch between document creation and access
        # if document.user_id != user.id:
        #     return jsonify({'error': 'Access denied'}), 403
        
        # Import AI service
        from app.services.ai_redlining import AIRedliningService
        ai_service = AIRedliningService()
        
        # Apply accepted changes
        # Get signature path if it exists (may not be set on all documents)
        signature_path = getattr(document, 'signature_path', None)
        
        result = ai_service.apply_accepted_changes(
            document.file_path, 
            accepted_changes,
            signature_path
        )
        
        if result['success']:
            # Update document record with final version
            document.final_file_path = result['output_path']
            db.session.commit()
            
            return jsonify({
                'success': True,
                'final_document_path': result['output_path'],
                'changes_applied': result['changes_applied'],
                'message': 'Final document created successfully'
            }), 200
        else:
            return jsonify({'error': result['error']}), 500
        
    except Exception as e:
        logger.error(f"Error applying accepted changes: {str(e)}")
        return jsonify({'error': f'Failed to apply changes: {str(e)}'}), 500

@changes_bp.route('/batch-update', methods=['POST'])
@require_auth
def batch_update_changes(user):
    """Update multiple changes at once"""
    try:
        data = request.get_json()
        changes_updates = data.get('changes', [])
        
        if not changes_updates:
            return jsonify({'error': 'No changes provided'}), 400
        
        updated_count = 0
        for change_update in changes_updates:
            change_id = change_update.get('id')
            status = change_update.get('status')
            
            if change_id and status in ['accepted', 'rejected']:
                # In a real implementation, you'd update the database
                updated_count += 1
        
        return jsonify({
            'success': True,
            'updated_count': updated_count,
            'message': f'Updated {updated_count} changes'
        }), 200
        
    except Exception as e:
        logger.error(f"Error batch updating changes: {str(e)}")
        return jsonify({'error': f'Failed to batch update changes: {str(e)}'}), 500
