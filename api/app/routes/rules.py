import logging
from flask import Blueprint, request, jsonify, current_app
from app import db
from functools import wraps

logger = logging.getLogger(__name__)
rules_bp = Blueprint('rules', __name__)

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

def require_admin(f):
    """Decorator to require admin role"""
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
        
        if user.role != 'ADMIN':
            return jsonify({'error': 'Admin access required'}), 403
        
        return f(user, *args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@rules_bp.route('/', methods=['GET'])
@require_auth
def list_rules(user):
    ProcessingRule = current_app.ProcessingRule
    
    if user.role == 'ADMIN':
        # Admin can see all active rules
        rules = ProcessingRule.query.filter_by(is_active=True).all()
    else:
        # Regular users can see all active rules (for viewing)
        rules = ProcessingRule.query.filter_by(is_active=True).all()
    
    return jsonify({
        'rules': [rule.to_dict() for rule in rules]
    })

@rules_bp.route('/', methods=['POST'])
@require_admin
def create_rule(user):
    data = request.get_json()
    
    if not data or not data.get('name') or not data.get('instruction') or not data.get('category'):
        return jsonify({'error': 'Name, instruction, and category are required'}), 400
    
    ProcessingRule = current_app.ProcessingRule
    rule = ProcessingRule(
        user_id=user.id,
        name=data['name'],
        instruction=data['instruction'],
        category=data['category'],
        is_active=True,
        is_global=False  # Rules created by admins are not global by default
    )
    
    db.session.add(rule)
    db.session.commit()
    
    return jsonify({
        'message': 'Rule created successfully',
        'rule': rule.to_dict()
    }), 201

@rules_bp.route('/<int:rule_id>', methods=['GET'])
@require_auth
def get_rule(user, rule_id):
    ProcessingRule = current_app.ProcessingRule
    rule = ProcessingRule.query.get(rule_id)
    
    if not rule:
        return jsonify({'error': 'Rule not found'}), 404
    
    if not rule.is_active:
        return jsonify({'error': 'Rule not found'}), 404
    
    return jsonify({
        'rule': rule.to_dict()
    })

@rules_bp.route('/<int:rule_id>', methods=['PUT'])
@require_admin
def update_rule(user, rule_id):
    data = request.get_json()
    
    ProcessingRule = current_app.ProcessingRule
    rule = ProcessingRule.query.get(rule_id)
    
    if not rule:
        return jsonify({'error': 'Rule not found'}), 404
    
    if rule.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Update fields
    if 'name' in data:
        rule.name = data['name']
    if 'instruction' in data:
        rule.instruction = data['instruction']
    if 'category' in data:
        rule.category = data['category']
    if 'is_active' in data:
        rule.is_active = data['is_active']
    
    db.session.commit()
    
    return jsonify({
        'message': 'Rule updated successfully',
        'rule': rule.to_dict()
    })

@rules_bp.route('/<int:rule_id>', methods=['DELETE'])
@require_admin
def delete_rule(user, rule_id):
    ProcessingRule = current_app.ProcessingRule
    rule = ProcessingRule.query.get(rule_id)
    
    if not rule:
        return jsonify({'error': 'Rule not found'}), 404
    
    if rule.user_id != user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Hard delete the rule
    db.session.delete(rule)
    db.session.commit()
    
    return jsonify({'message': 'Rule deleted successfully'})

@rules_bp.route('/fix-hardcoded-values', methods=['POST'])
@require_admin
def fix_hardcoded_values(user):
    """Remove hardcoded company/person names from rules"""
    ProcessingRule = current_app.ProcessingRule
    
    # Get all rules
    rules = ProcessingRule.query.all()
    
    updated_rules = []
    
    for rule in rules:
        original_instruction = rule.instruction
        updated_instruction = original_instruction
        
        # Replace hardcoded company names with placeholder
        hardcoded_companies = [
            'JMC Investment LLC',
            'JMC Investment',
            'Welch Capital Partners',
        ]
        
        for company in hardcoded_companies:
            if company in updated_instruction:
                updated_instruction = updated_instruction.replace(company, '[FIRM_NAME]')
        
        # Replace hardcoded person names with placeholder
        hardcoded_names = [
            'John Bagge',
        ]
        
        for name in hardcoded_names:
            if name in updated_instruction:
                updated_instruction = updated_instruction.replace(name, '[SIGNER_NAME]')
        
        # Replace hardcoded titles with placeholder
        hardcoded_titles = [
            'Vice President',
        ]
        
        for title in hardcoded_titles:
            if title in updated_instruction:
                updated_instruction = updated_instruction.replace(title, '[TITLE]')
        
        # If instruction was modified, update it
        if updated_instruction != original_instruction:
            rule.instruction = updated_instruction
            updated_rules.append({
                'id': rule.id,
                'name': rule.name,
                'old_instruction': original_instruction,
                'new_instruction': updated_instruction
            })
    
    db.session.commit()
    
    return jsonify({
        'message': f'Successfully updated {len(updated_rules)} rule(s)',
        'updated_rules': updated_rules
    }), 200

@rules_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get available rule categories"""
    categories = [
        'Term Modification',
        'Party Information',
        'Firm Details',
        'Signature Requirements',
        'Confidentiality',
        'Liability',
        'Other'
    ]
    
    return jsonify({'categories': categories})

@rules_bp.route('/templates', methods=['GET'])
def get_rule_templates():
    """Get rule templates for common scenarios"""
    templates = [
        {
            'name': 'Standard NDA Terms',
            'instruction': 'Ensure standard NDA terms are present and properly defined',
            'category': 'Term Modification'
        },
        {
            'name': 'Confidentiality Duration',
            'instruction': 'Verify confidentiality obligations extend for appropriate duration',
            'category': 'Confidentiality'
        },
        {
            'name': 'Liability Limitations',
            'instruction': 'Check for reasonable liability limitations and exclusions',
            'category': 'Liability'
        }
    ]
    
    return jsonify({'templates': templates})
