from models.user import User
from datetime import datetime


def create_user(email,password,role,db):

    user = User(email=email,password=password,role=role)

    db.add(user)
    db.commit()

    db.refresh(user)


    return user


def get_user_by_email(email,db):
    return db.query(User).filter(User.email == email).first()


def set_verification_token(user, token_hash, expires_at, sent_at, db):
    user.verification_token_hash = token_hash
    user.verification_token_expires_at = expires_at
    user.verification_token_sent_at = sent_at
    user.is_verified = False

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def clear_verification_token(user, db):
    user.verification_token_hash = None
    user.verification_token_expires_at = None
    user.verification_token_sent_at = None

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_verification_hash(token_hash, db):
    return db.query(User).filter(User.verification_token_hash == token_hash).first()
