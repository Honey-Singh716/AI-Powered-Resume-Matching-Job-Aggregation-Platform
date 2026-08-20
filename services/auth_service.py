from passlib.context import CryptContext
from datetime import datetime,timedelta,timezone
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
import os

from database import get_db
from sqlalchemy.orm import Session

from repositories.user_repo_ext import get_user_by_email

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


from dotenv import load_dotenv
load_dotenv()

expire_minutes = 30
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable is not set. Add it to your .env file.")
ALGORITHM = "HS256"

#Password hashing

def hash_password(password:str):
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)



def create_access_token(data:dict,expires_delta: int=None):

    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_delta if expires_delta else expire_minutes)

    to_encode.update({"exp" : expire})


    encoded_jwt = jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)


    return encoded_jwt



def current_user(token: str = Depends(oauth2_scheme),db: Session = Depends(get_db)):

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        if email is None:
            raise credentials_exception
    
    except JWTError:
        raise credentials_exception

    user = get_user_by_email(email,db)


    if user is None:
         raise credentials_exception
    
    # Block access for unverified users
    if not getattr(user, 'is_verified', False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Please verify your email before logging in.")

    return user