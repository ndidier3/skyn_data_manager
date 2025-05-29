"""
API routes for SDM web application.
"""

from flask import Flask, jsonify, request, current_app
from flask_cors import CORS
from .endpoints import studies, curves, events, days, settings
import logging

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Configure logging
    logging.basicConfig(level=logging.DEBUG)
    app.logger.setLevel(logging.DEBUG)
    
    # Enable CORS for all routes with specific settings for Vue.js app
    CORS(app, 
         resources={r"/*": {
             "origins": ["http://localhost:8080", "http://127.0.0.1:8080"],
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
             "allow_headers": ["Content-Type", "Authorization"],
             "supports_credentials": True
         }},
         supports_credentials=True)
    
    # Add request debugging
    @app.before_request
    def log_request_info():
        app.logger.debug('=' * 50)
        app.logger.debug('New Request:')
        app.logger.debug('Request URL: %s', request.url)
        app.logger.debug('Request Method: %s', request.method)
        app.logger.debug('Request Headers: %s', dict(request.headers))
        app.logger.debug('Request Body: %s', request.get_data())
        app.logger.debug('Request Args: %s', dict(request.args))
        
        # Handle OPTIONS requests
        if request.method == 'OPTIONS':
            response = jsonify({})
            origin = request.headers.get('Origin', 'http://localhost:8080')
            response.headers.add('Access-Control-Allow-Origin', origin)
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
            response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            return response
    
    @app.after_request
    def after_request(response):
        app.logger.debug('Response Status: %s', response.status)
        app.logger.debug('Response Headers: %s', dict(response.headers))
        origin = request.headers.get('Origin', 'http://localhost:8080')
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        app.logger.debug('=' * 50)
        return response
    
    @app.errorhandler(403)
    def handle_403(e):
        app.logger.error('403 Forbidden Error: %s', str(e))
        app.logger.error('Request URL: %s', request.url)
        app.logger.error('Request Method: %s', request.method)
        app.logger.error('Request Headers: %s', dict(request.headers))
        app.logger.error('Request Body: %s', request.get_data())
        app.logger.error('Request Args: %s', dict(request.args))
        app.logger.error('Stack Trace:', exc_info=True)
        
        response = jsonify({
            'error': 'Forbidden',
            'message': str(e),
            'details': {
                'url': request.url,
                'method': request.method,
                'headers': dict(request.headers)
            }
        })
        origin = request.headers.get('Origin', 'http://localhost:8080')
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
        response.headers.add('Access-Control-Allow-Credentials', 'true')
        return response, 403
    
    # Add a simple test route
    @app.route('/')
    def index():
        app.logger.info('Index endpoint called')
        return jsonify({"message": "API is working"})
    
    @app.route('/test')
    def test():
        app.logger.info('Test endpoint called')
        return jsonify({"message": "Test endpoint is working"})
    
    # Register blueprints with explicit URL prefixes
    app.register_blueprint(studies.studies_bp, url_prefix='/api')
    app.register_blueprint(curves.curves_bp, url_prefix='/api')
    app.register_blueprint(events.events_bp, url_prefix='/api')
    app.register_blueprint(days.days_bp, url_prefix='/api')
    app.register_blueprint(settings.settings_bp, url_prefix='/api')
    
    # Print all registered routes for debugging
    print("\nRegistered routes:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule}")
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000) 