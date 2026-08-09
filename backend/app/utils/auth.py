from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.models.user import User
from app.services.supabase_auth import supabase_auth_verifier
import os

# Configuration
SECRET_KEY = "EDUAI_SECRET_KEY_KEEP_IT_SAFE"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 1 week

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token or token in ("null", "undefined"):
        raise credentials_exception

    try:
        if os.getenv("AUTH_PROVIDER", "legacy").lower() == "supabase":
            payload = supabase_auth_verifier.verify(token)
            auth_user_id = payload.get("sub")
            email = payload.get("email")
            user = await User.find_one(
                User.auth_user_id == auth_user_id
            ) if auth_user_id else None
            if user is None and email:
                user = await User.find_one(User.email == email)
                if user is not None and not user.auth_user_id:
                    user.auth_user_id = auth_user_id
                    await user.save()
        else:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            email: str = payload.get("sub")
            if email is None:
                raise credentials_exception
            user = await User.find_one(User.email == email)
    except JWTError:
        raise credentials_exception

    if user is None:
        raise credentials_exception

    # Session timeout check (15 minutes = 900 seconds)
    now = datetime.utcnow()
    if user.last_active and (now - user.last_active).total_seconds() > 900:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session timeout due to inactivity",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last active timestamp
    user.last_active = now
    await user.save()

    # Block users that haven't been approved yet
    if hasattr(user, "status") and user.status and user.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account is {user.status}. Please wait for admin approval.",
        )
    return user

async def get_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have enough privileges"
        )
    return current_user
