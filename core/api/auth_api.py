from fastapi import Depends, HTTPException, APIRouter, Body
from sqlmodel import Session

from core.auth.auth_handler import authenticate_user, create_access_token, create_refresh_token, verify_refresh_token
from core.configs.database import get_db
from core.schemas.token import Token

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=Token)
def login(username: str = Body(...), password: str = Body(...), session: Session = Depends(get_db)):
    user = authenticate_user(session, username, password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(user.dict())
    refresh_token = create_refresh_token(user)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,  # include in response
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
def refresh_token(refresh_token: str = Body(...)):
    payload = verify_refresh_token(refresh_token)
    new_access_token = create_access_token(payload)
    return {
        "access_token": new_access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }
