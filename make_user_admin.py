#!/usr/bin/env python3
"""
Script to make an existing user an admin
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')
load_dotenv('.env')

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def make_user_admin():
    # Use Railway database URL
    railway_db_url = "postgresql://postgres:NXLOBfpFlNRrTPlPOYkCSBZIkWQMwYnR@containers-us-west-146.railway.app:5432/railway"
    os.environ['DATABASE_URL'] = railway_db_url
    
    sys.path.insert(0, 'api')
    from app import create_app, db
    
    app = create_app()
    
    with app.app_context():
        User = app.User
        
        # Get the email of the user you just created
        user_email = input("Enter the email of the user you want to make admin: ")
        
        # Find the user
        user = User.query.filter_by(email=user_email).first()
        
        if not user:
            print(f"❌ User with email {user_email} not found!")
            return
        
        print(f"Found user: {user.email}")
        print(f"Current role: {user.role}")
        
        # Change role to ADMIN
        user.role = 'ADMIN'
        
        try:
            db.session.commit()
            print("✅ User role changed to ADMIN successfully!")
            print(f"Email: {user.email}")
            print(f"New Role: {user.role}")
        except Exception as e:
            print(f"❌ Error: {e}")
            db.session.rollback()

if __name__ == "__main__":
    make_user_admin()
