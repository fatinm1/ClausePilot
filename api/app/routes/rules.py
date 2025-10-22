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

@rules_bp.route('/improve-vague-rules', methods=['POST'])
def improve_vague_rules():
    """Make vague rules more specific to prevent over-redlining"""
    ProcessingRule = current_app.ProcessingRule
    
    updates = []
    
    # Rule #7: Make it VERY specific about what to change
    rule_7 = ProcessingRule.query.get(7)
    if rule_7:
        rule_7.instruction = "In Section 13 (Term section ONLY), if the document says 'three years' or 'five years', change to 'two (2) years'. Do NOT change any text in the opening paragraphs or parenthetical definitions. ONLY change duration in the numbered Term section."
        updates.append({'id': 7, 'name': rule_7.name, 'new_instruction': rule_7.instruction})
    
    # Rule #12: Make it more specific about what to change
    rule_12 = ProcessingRule.query.get(12)
    if rule_12:
        rule_12.instruction = "If the document specifies notice periods (e.g., '3 days notice', '10 days notice'), change them to '5 business days notice'. Do NOT change other references to time periods."
        updates.append({'id': 12, 'name': rule_12.name, 'new_instruction': rule_12.instruction})
    
    # Rule #13: Make it more specific
    rule_13 = ProcessingRule.query.get(13)
    if rule_13:
        rule_13.instruction = "In the 'Term' or 'Survival' section, if confidentiality obligations survive for more than 2 years, change to '2 years after termination'. Trade secrets should survive indefinitely. Do NOT change other references."
        updates.append({'id': 13, 'name': rule_13.name, 'new_instruction': rule_13.instruction})
    
    db.session.commit()
    
    return jsonify({
        'message': f'Improved {len(updates)} rule(s) to be more specific',
        'updates': updates
    }), 200

@rules_bp.route('/disable-problematic-rules', methods=['POST'])
def disable_problematic_rules():
    """Disable rules that are causing over-redlining"""
    ProcessingRule = current_app.ProcessingRule
    
    # Rule #8 is causing Company to be replaced everywhere
    rule_8 = ProcessingRule.query.get(8)
    if rule_8:
        rule_8.is_active = False
        db.session.commit()
        return jsonify({
            'message': 'Disabled problematic rule #8 (Parties Name Update)',
            'rule': rule_8.to_dict()
        }), 200
    else:
        return jsonify({'message': 'Rule #8 not found'}), 404

@rules_bp.route('/fix-hardcoded-values', methods=['POST'])
def fix_hardcoded_values():
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
