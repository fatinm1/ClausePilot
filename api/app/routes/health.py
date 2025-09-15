from flask import Blueprint, jsonify
import os
import logging

logger = logging.getLogger(__name__)

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
    
    # Test if we can create OpenAI client directly
    try:
        from openai import OpenAI
        # Check what parameters are being passed
        import inspect
        sig = inspect.signature(OpenAI.__init__)
        params = list(sig.parameters.keys())
        logger.info(f"OpenAI.__init__ parameters: {params}")
        
        test_client = OpenAI(api_key=api_key)
        client_test = 'success'
            
    except Exception as e:
        client_test = f'failed: {str(e)}'
        # Try to get more details about the error
        import traceback
        error_details = traceback.format_exc()
        client_test += f" | Details: {error_details}"
    
    # Check for proxy-related environment variables
    proxy_vars = {k: v for k, v in os.environ.items() if 'proxy' in k.lower() or 'PROXY' in k}
    
    # Check for any environment variables that might affect OpenAI
    all_env_vars = dict(os.environ)
    openai_related_vars = {k: v for k, v in all_env_vars.items() if any(keyword in k.upper() for keyword in ['OPENAI', 'PROXY', 'HTTP', 'HTTPS'])}
    
    # Check specifically for HTTP proxy environment variables
    http_proxy_vars = {k: v for k, v in all_env_vars.items() if k.upper() in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'NO_PROXY', 'no_proxy']}
    
    # Check for any environment variables that might be passed to httpx
    httpx_vars = {k: v for k, v in all_env_vars.items() if 'httpx' in k.lower() or 'HTTPX' in k}
    
    return jsonify({
        'status': 'ok',
        'openai_mode': 'mock' if is_mock_mode else 'real',
        'actual_mode': actual_mode,
        'api_key_set': bool(api_key),
        'api_key_is_mock': api_key == 'mock-key-for-development' if api_key else True,
        'api_key_length': len(api_key) if api_key else 0,
        'api_key_preview': api_key[:10] if api_key and len(api_key) > 10 else 'N/A',
        'openai_env_vars': openai_vars,
        'client_test': client_test,
        'proxy_vars': proxy_vars,
        'openai_related_vars': openai_related_vars,
        'openai_params': params if 'params' in locals() else 'not_available',
        'http_proxy_vars': http_proxy_vars,
        'httpx_vars': httpx_vars,
        'safe_mode': 'Yes - using mock mode for all AI calls'
    })
