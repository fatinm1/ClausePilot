#!/usr/bin/env python3
"""
Simple script to create admin user using existing app structure
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')
load_dotenv('.env')

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def create_admin():
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
            print("✅ Admin created!")
            print(f"Email: {admin_email}")
            print(f"Password: admin123")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    create_admin()
