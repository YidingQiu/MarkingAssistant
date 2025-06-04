from datetime import datetime, timedelta, UTC
from typing import Dict

from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlmodel import Session, select
from fastapi import HTTPException, status, Depends

from core.configs import settings
from core.models import User
from core.schemas.user_schema import UserResponse

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def authenticate_user(db_session: Session, username: str, password: str):
    statement = select(User).where(User.username == username)
    result = db_session.exec(statement).first()
    if not result or not verify_password(password, result.password):
        return None
    return result

def create_access_token(user: Dict, expires_delta: timedelta | None = None):
    to_encode = {
        "sub": user.get("username") or user.get("sub"),
        "id": user["id"],
        "email": user["email"],
        "role": user["role"],
    }
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_ACCESS_SECRET, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme)) -> UserResponse:
    try:
        payload = jwt.decode(token, settings.JWT_ACCESS_SECRET, algorithms=[ALGORITHM])
        return UserResponse.model_validate({
            "id": payload.get("id"),
            "username": payload.get("sub"),
            "email": payload.get("email"),
            "role": payload.get("role"),
        })
        # username, role = payload.get("sub"), payload.get("role")
        # if username is None:
        #     raise credentials_exception
        # return {username, role}
    except JWTError:
        raise credentials_exception

def create_refresh_token(user: User):
    to_encode = {
        "sub": user.username,
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "exp": datetime.now(UTC) + timedelta(days=30),
    }
    return jwt.encode(to_encode, settings.JWT_REFRESH_SECRET, algorithm=ALGORITHM)

def verify_refresh_token(token: str):
    try:
        return jwt.decode(token, settings.JWT_REFRESH_SECRET, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)
