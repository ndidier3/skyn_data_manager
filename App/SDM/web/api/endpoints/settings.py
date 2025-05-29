"""
Settings endpoints for SDM web application.
"""

from flask import Blueprint, jsonify, request, current_app
from App.SDM.Scripts.Test.test_settings import (
    smooth_and_impute_attrs,
    curve_attrs,
    day_attrs,
    gaps_and_non_wear_attrs
)

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings/test', methods=['GET'])
def test_settings():
    """Test endpoint to verify settings API is working."""
    current_app.logger.info('Settings test endpoint called')
    current_app.logger.info('Request method: %s', request.method)
    current_app.logger.info('Request headers: %s', dict(request.headers))
    
    response = jsonify({"message": "Settings API is working"})
    origin = request.headers.get('Origin', 'http://localhost:8080')
    response.headers.add('Access-Control-Allow-Origin', origin)
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

@settings_bp.route('/settings/default', methods=['GET'])
def get_default_settings():
    """Get default settings for the application."""
    current_app.logger.info('Default settings endpoint called')
    current_app.logger.info('Request method: %s', request.method)
    current_app.logger.info('Request headers: %s', dict(request.headers))
    
    try:
        # Log imported values for debugging
        current_app.logger.info('Imported values:')
        current_app.logger.info('smooth_and_impute_attrs: %s', smooth_and_impute_attrs)
        current_app.logger.info('curve_attrs: %s', curve_attrs)
        current_app.logger.info('day_attrs: %s', day_attrs)
        current_app.logger.info('gaps_and_non_wear_attrs: %s', gaps_and_non_wear_attrs)
        
        default_settings = {
            'smooth_and_impute': smooth_and_impute_attrs,
            'curve': curve_attrs,
            'day': day_attrs,
            'gaps_and_non_wear': gaps_and_non_wear_attrs
        }
        
        response = jsonify(default_settings)
        origin = request.headers.get('Origin', 'http://localhost:8080')
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
        
    except Exception as e:
        current_app.logger.error('Error in get_default_settings: %s', str(e))
        response = jsonify({
            'error': str(e),
            'type': type(e).__name__
        }), 500
        origin = request.headers.get('Origin', 'http://localhost:8080')
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response

@settings_bp.route('/settings/validate', methods=['POST'])
def validate_settings():
    """Validate settings provided by the client."""
    current_app.logger.info('Validate settings endpoint called')
    current_app.logger.info('Request method: %s', request.method)
    current_app.logger.info('Request headers: %s', dict(request.headers))
    
    try:
        settings = request.get_json()
        if not settings:
            response = jsonify({'error': 'No settings provided'}), 400
            origin = request.headers.get('Origin', 'http://localhost:8080')
            response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            return response
            
        required_sections = ['smooth_and_impute', 'curve', 'day', 'gaps_and_non_wear']
        missing_sections = [section for section in required_sections if section not in settings]
        
        if missing_sections:
            response = jsonify({
                'error': f'Missing required sections: {", ".join(missing_sections)}'
            }), 400
            origin = request.headers.get('Origin', 'http://localhost:8080')
            response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            return response
            
        response = jsonify({'message': 'Settings are valid'})
        origin = request.headers.get('Origin', 'http://localhost:8080')
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response
        
    except Exception as e:
        current_app.logger.error('Error in validate_settings: %s', str(e))
        response = jsonify({
            'error': str(e),
            'type': type(e).__name__
        }), 500
        origin = request.headers.get('Origin', 'http://localhost:8080')
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response 