from flask import Blueprint, jsonify, request
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__)

@health_bp.route('/healthz', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'version': '1.0.1-rule-preprocessing-active',  # DEPLOYED: Rule preprocessing is active!
        'timestamp': datetime.now().isoformat(),
        'features': ['rule_preprocessing', 'firm_details_override']
    })

@health_bp.route('/test-firm-details', methods=['POST'])
def test_firm_details():
    """Test endpoint to see what firm details are received"""
    try:
        data = request.get_json() or {}
        firm_details = data.get('firm_details', {})
        
        return jsonify({
            'status': 'success',
            'received_data': data,
            'firm_details': firm_details,
            'firm_details_keys': list(firm_details.keys()) if firm_details else [],
            'firm_details_values': {k: v for k, v in firm_details.items()} if firm_details else {}
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500

@health_bp.route('/debug', methods=['GET'])
def debug_info():
    """Debug endpoint to check configuration without exposing sensitive data"""
    api_key = os.getenv('OPENAI_API_KEY')
    
    # Check if we're in mock mode
    is_mock_mode = not api_key or api_key == 'mock-key-for-development'
    
    # Test actual AI service behavior
    actual_mode = 'not_initialized'
    test_analyze_result = 'not_run'
    analyze_mode = 'not_run'
    
    try:
        from app.services.ai_redlining import AIRedliningService
        ai_service = AIRedliningService()
        actual_mode = 'mock' if ai_service.client is None else 'real'
        
        # Test analyze_document to see what happens
        try:
            test_doc_text = "This is a test document with Dear NAME: and For: Company and Title: _______________________________"
            test_rules = [{"name": "Test Rule", "instruction": "Test instruction", "category": "test"}]
            test_firm_details = {"firm_name": "Test Firm", "signatory_name": "Test Signer", "title": "Test Title"}
            test_analyze_result = ai_service.analyze_document(test_doc_text, test_rules, test_firm_details)
            # Check if it used real API or mock
            if 'modifications' in str(test_analyze_result):
                analyze_mode = 'returned_modifications'
            else:
                analyze_mode = 'unknown_format'
        except Exception as analyze_error:
            test_analyze_result = {"error": str(analyze_error), "type": type(analyze_error).__name__}
            analyze_mode = 'error'
            import traceback
            test_analyze_result["traceback"] = traceback.format_exc()
    except Exception as e:
        actual_mode = 'error'
        test_analyze_result = {"error": str(e), "type": type(e).__name__}
        analyze_mode = 'init_error'
        import traceback
        test_analyze_result["traceback"] = traceback.format_exc()
    
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
        'analyze_document_test': test_analyze_result,
        'analyze_mode': analyze_mode,
        'safe_mode': 'Yes - using mock mode for all AI calls' if actual_mode == 'mock' else 'No - using real OpenAI API'
    })
