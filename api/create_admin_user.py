#!/usr/bin/env python3
"""
Script to create an admin user in the database
Run this script to create the first admin user
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')
load_dotenv('.env')

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import define_models

def create_admin_user():
    app = create_app()
    
    with app.app_context():
        # Get the User model
        User, Document, ProcessingRule, ProcessingJob, UserRole, DocumentStatus = define_models(db)
        
        # Check if admin already exists
        admin_email = "admin@ndaredline.com"
        existing_admin = User.query.filter_by(email=admin_email).first()
        
        if existing_admin:
            print(f"Admin user with email {admin_email} already exists!")
            print(f"Admin ID: {existing_admin.id}")
            print(f"Admin Role: {existing_admin.role}")
            return
        
        # Create admin user
        admin_user = User(
            email=admin_email,
            role='ADMIN',
            is_active=True
        )
        admin_user.set_password('admin123')  # Default password
        
        try:
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Admin user created successfully!")
            print(f"Email: {admin_email}")
            print(f"Password: admin123")
            print(f"Role: ADMIN")
            print("\n⚠️  IMPORTANT: Change the password after first login!")
        except Exception as e:
            print(f"❌ Error creating admin user: {e}")
            db.session.rollback()

if __name__ == "__main__":
    create_admin_user()
