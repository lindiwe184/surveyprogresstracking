#!/usr/bin/env python3
"""
Admin setup script for the Survey Tracking System.
This script creates the superadmin user and initializes the database.
"""

import os
import sys
from dotenv import load_dotenv

# Add the backend directory to the path
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Load environment variables
load_dotenv()

from kobo_app import create_app
from models import db, User

def setup_admin():
    """Set up the admin user and database."""
    print("Setting up admin user and database...")
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        # Create all database tables
        db.create_all()
        print("✓ Database tables created")
        
        # Check if admin user already exists
        admin_user = User.query.filter_by(username='admin').first()
        
        if admin_user:
            print(f"✓ Admin user '{admin_user.username}' already exists")
            
            # Update password if needed
            if not admin_user.check_password('Amazing@2001'):
                admin_user.set_password('Amazing@2001')
                db.session.commit()
                print("✓ Admin password updated")
            
            # Ensure superadmin role
            if admin_user.role != 'superadmin':
                admin_user.role = 'superadmin'
                db.session.commit()
                print("✓ Admin role updated to superadmin")
                
        else:
            # Create new admin user
            admin_user = User(
                username='admin',
                email='lmabena@nsa.org.na',
                role='superadmin',
                is_active=True
            )
            admin_user.set_password('Amazing@2001')
            
            db.session.add(admin_user)
            db.session.commit()
            print("✓ Admin user created successfully")
        
        print(f"""
Admin User Configuration:
========================
Username: {admin_user.username}
Email: {admin_user.email}
Role: {admin_user.role}
Status: {'Active' if admin_user.is_active else 'Inactive'}
Created: {admin_user.created_at}

Login Credentials:
Username: admin
Password: Amazing@2001
Email: lmabena@nsa.org.na

The admin user has been configured successfully!
""")

if __name__ == '__main__':
    try:
        setup_admin()
    except Exception as e:
        print(f"Error setting up admin user: {e}")
        sys.exit(1)