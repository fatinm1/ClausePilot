import os
from app import create_app, db, migrate

app = create_app()

if __name__ == '__main__':
    # Run database migrations on startup
    with app.app_context():
        try:
            print("Running database migrations...")
            from flask_migrate import upgrade
            upgrade()
            print("Database migrations completed successfully!")
        except Exception as e:
            print(f"Migration error (this might be normal on first run): {e}")
            print("Attempting to create tables directly...")
            try:
                db.create_all()
                print("Database tables created successfully!")
            except Exception as create_error:
                print(f"Failed to create tables: {create_error}")
    
    # Get port from environment variable (Railway sets this)
    port = int(os.environ.get('PORT', 5001))
    # Disable debug in production
    debug = os.environ.get('FLASK_ENV') != 'production'
    
    print("=" * 80)
    print("🚀 VERSION: 1.2.0-WORD-TRACK-CHANGES-ACTIVE")
    print("✅ FEATURE: Word Track Changes integration (accept/reject changes)")
    print("✅ FEATURE: Flexible date pattern matching")
    print("✅ FEATURE: Auto-fixes for firm details and term changes")
    print("=" * 80)
    
    # Configure for larger file uploads
    app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching for uploaded files
    
    app.run(host='0.0.0.0', port=port, debug=debug)
