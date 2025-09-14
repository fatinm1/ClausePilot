#!/usr/bin/env python3
"""
Script to create a test user for development
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User

def create_test_user():
    app = create_app()
    
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(email='test@example.com').first()
        if existing_user:
            print(f"User already exists with ID: {existing_user.id}")
            return existing_user.id
        
        # Create test user
        user = User(email='test@example.com')
        user.set_password('password123')
        
        db.session.add(user)
        db.session.commit()
        
        print(f"Created test user with ID: {user.id}")
        print(f"Email: {user.email}")
        print(f"Password: password123")
        
        return user.id

if __name__ == "__main__":
    create_test_user()
