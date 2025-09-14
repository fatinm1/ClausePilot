#!/usr/bin/env python3
"""
Script to create admin user in Railway database
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')
load_dotenv('.env')

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_railway_admin():
    # Set Railway database URL (using public URL)
    railway_db_url = "postgresql://postgres:NXLOBfpFlNRrTPlPOYkCSBZIkWQMwYnR@containers-us-west-146.railway.app:5432/railway"
    
    # Override the DATABASE_URL for this script
    os.environ['DATABASE_URL'] = railway_db_url
    
    sys.path.insert(0, 'api')
    from app import create_app, db
    
    app = create_app()
    
    with app.app_context():
        # Use the existing User model from the app
        User = app.User
        
        # Check if admin exists
        admin_email = "admin@ndaredline.com"
        existing = User.query.filter_by(email=admin_email).first()
        
        if existing:
            print(f"Admin already exists: {admin_email}")
            print(f"Role: {existing.role}")
            return
        
        # Create admin
        admin = User(
            email=admin_email,
            role='ADMIN',
            is_active=True
        )
        admin.set_password('admin123')
        
        try:
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin created in Railway database!")
            print(f"Email: {admin_email}")
            print(f"Password: admin123")
            print(f"Role: ADMIN")
        except Exception as e:
            print(f"❌ Error: {e}")
            db.session.rollback()

if __name__ == "__main__":
    create_railway_admin()
