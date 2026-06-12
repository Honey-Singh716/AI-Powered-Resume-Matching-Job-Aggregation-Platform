from fastapi import HTTPException

from repositories.user_repo import create_user
from repositories.user_repo import get_user_by_email
from services.auth_service import hash_password,verify_password,create_access_token



def save_user(user_data,db):

    email = user_data.email
    existing_user = get_user_by_email(email,db)
    
    if existing_user:
        raise  HTTPException(status_code=400, detail="User with this email already exists")
 

    password = user_data.password
    hashed_password = hash_password(password)
    role = user_data.role

    return create_user(email,hashed_password,role,db)


def login_user(login_data,db):

    user = get_user_by_email(login_data.email,db)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    

    if not verify_password(login_data.password,user.password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    

    token = create_access_token({
        "sub" : user.email,
        "role": user.role
    })

    return {
        "access_token":token,
        "token_type" : "bearer"
    }