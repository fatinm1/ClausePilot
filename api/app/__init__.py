from flask import Flask, send_from_directory, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from config import Config
import os

db = SQLAlchemy()
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Configure file upload limits
    app.config['MAX_CONTENT_LENGTH'] = config_class.MAX_CONTENT_LENGTH
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # CORS setup
    CORS(app, origins=app.config['CORS_ORIGINS'], supports_credentials=True)
    
    # Define models after db is initialized
    with app.app_context():
        from app.models import define_models
        User, Document, ProcessingRule, ProcessingJob, UserRole, DocumentStatus = define_models(db)
        
        # Make models available globally
        app.User = User
        app.Document = Document
        app.ProcessingRule = ProcessingRule
        app.ProcessingJob = ProcessingJob
        app.UserRole = UserRole
        app.DocumentStatus = DocumentStatus
    
    # Register blueprints
    from app.routes.health import health_bp
    from app.routes.auth import auth_bp
    from app.routes.documents import documents_bp
    from app.routes.rules import rules_bp
    from app.routes.admin import admin_bp
    from app.routes.signatures import signatures_bp
    from app.routes.changes import changes_bp
    
    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp, url_prefix='/v1/auth')
    app.register_blueprint(documents_bp, url_prefix='/v1/documents')
    app.register_blueprint(rules_bp, url_prefix='/v1/rules')
    app.register_blueprint(admin_bp, url_prefix='/v1/admin')
    app.register_blueprint(signatures_bp, url_prefix='/v1/signatures')
    app.register_blueprint(changes_bp, url_prefix='/v1/changes')
    
    # Serve frontend static files
    @app.route('/')
    def serve_frontend():
        return send_file(os.path.join(app.root_path, '..', 'web', 'out', 'index.html'))
    
    @app.route('/<path:path>')
    def serve_static(path):
        # Handle API routes
        if path.startswith('v1/'):
            return "API route not found", 404
        
        # Serve static files
        static_path = os.path.join(app.root_path, '..', 'web', 'out', path)
        if os.path.exists(static_path) and os.path.isfile(static_path):
            return send_file(static_path)
        
        # For SPA routing, serve index.html for any non-API route
        return send_file(os.path.join(app.root_path, '..', 'web', 'out', 'index.html'))
    
    # Error handler for file too large
    @app.errorhandler(413)
    def too_large(e):
        return jsonify({
            'error': 'File too large',
            'message': 'File size exceeds the maximum allowed limit of 50MB',
            'max_size': '50MB'
        }), 413
    
    # Don't create tables here - use migrations instead
    # with app.app_context():
    #     db.create_all()
    
    return app
