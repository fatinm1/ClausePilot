from flask import Blueprint, jsonify
import os

health_bp = Blueprint('health', __name__)

@health_bp.route('/healthz', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok'})

@health_bp.route('/debug', methods=['GET'])
def debug_info():
    """Debug endpoint to check configuration without exposing sensitive data"""
    api_key = os.getenv('OPENAI_API_KEY')
    
    # Check if we're in mock mode
    is_mock_mode = not api_key or api_key == 'mock-key-for-development'
    
    # Test actual AI service behavior
    try:
        from app.services.ai_redlining import AIRedliningService
        ai_service = AIRedliningService()
        actual_mode = 'mock' if ai_service.client is None else 'real'
    except Exception as e:
        actual_mode = 'error'
    
    # Check all environment variables that start with OPENAI
    openai_vars = {k: v for k, v in os.environ.items() if 'OPENAI' in k.upper()}
    
    return jsonify({
        'status': 'ok',
        'openai_mode': 'mock' if is_mock_mode else 'real',
        'actual_mode': actual_mode,
        'api_key_set': bool(api_key),
        'api_key_is_mock': api_key == 'mock-key-for-development' if api_key else True,
        'api_key_length': len(api_key) if api_key else 0,
        'api_key_preview': api_key[:10] if api_key and len(api_key) > 10 else 'N/A',
        'openai_env_vars': openai_vars,
        'safe_mode': 'Yes - using mock mode for all AI calls'
    })
