#!/usr/bin/env python3
"""Script to reset admin user password"""

import sys
import os

# Add the app directory to the path
sys.path.append('/app')

from app.database import SessionLocal
from app.services.auth import AuthService
from app.models.user import User
from app.config import settings

def reset_admin_password():
    """Reset the admin user password"""
    print("🔄 Resetting admin user password...")
    
    auth_service = AuthService()
    db = SessionLocal()
    
    try:
        # Find the admin user
        admin_user = db.query(User).filter(User.username == settings.admin_username).first()
        
        if not admin_user:
            print("❌ Admin user not found, creating new one...")
            # Create new admin user
            hashed_password = auth_service.hash_password(settings.admin_password)
            admin_user = User(
                username=settings.admin_username,
                email=settings.admin_email,
                hashed_password=hashed_password,
                full_name="Administrator",
                is_active=True,
                is_superuser=True
            )
            db.add(admin_user)
            db.commit()
            print(f"✅ Created new admin user: {settings.admin_username}")
        else:
            print(f"👤 Found admin user: {admin_user.username}")
            # Update the password
            new_hashed_password = auth_service.hash_password(settings.admin_password)
            admin_user.hashed_password = new_hashed_password
            admin_user.is_active = True
            db.commit()
            print(f"✅ Updated password for admin user: {settings.admin_username}")
        
        # Test the password
        if auth_service.verify_password(settings.admin_password, admin_user.hashed_password):
            print("✅ Password verification successful")
        else:
            print("❌ Password verification failed")
            
        print(f"🔑 Admin credentials:")
        print(f"   Username: {settings.admin_username}")
        print(f"   Password: {settings.admin_password}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_admin_password()

