"""
Script to create a new admin user or promote an existing one.

Usage:
    python scripts/create_admin.py <email> <password>
"""
import sys
import os

# Make sure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from database import SessionLocal
from models.user import User
from services.auth_service import hash_password


def promote_to_admin(email: str, password: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"[INFO] User not found. Creating new admin user: {email}")
            hashed_pw = hash_password(password)
            user = User(
                email=email,
                password=hashed_pw,
                role="admin",
                is_verified=True
            )
            db.add(user)
            db.commit()
            print(f"[SUCCESS] Admin user '{email}' created successfully.")
            return True

        if user.role == "admin":
            print(f"[INFO] User {email} is already an admin.")
            # Also update password just in case
            user.password = hash_password(password)
            user.is_verified = True
            db.commit()
            print("[INFO] Password updated.")
            return True

        old_role = user.role
        user.role = "admin"
        user.is_verified = True  # Ensure admin is verified
        user.password = hash_password(password)
        db.commit()
        print(f"[SUCCESS] User '{email}' promoted from '{old_role}' to 'admin'.")
        print(f"[INFO] Password updated and is_verified set to True.")
        return True
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python scripts/create_admin.py <email> <password>")
        sys.exit(1)

    email = sys.argv[1]
    password = sys.argv[2]
    success = promote_to_admin(email, password)
    sys.exit(0 if success else 1)
