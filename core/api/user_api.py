from typing import List

from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session

from core.auth.auth_handler import get_current_user
from core.schemas.user_schema import UserCreateRequest, UserResponse, UserSetupRequest
from core.services import user_service
from core.configs.database import get_db

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=UserResponse)
def create_user(user_req: UserCreateRequest, db: Session = Depends(get_db)):
    return user_service.create_user(user_req, db)

@router.get("/", response_model=List[UserResponse])
def list_users(db: Session = Depends(get_db)):
    users = user_service.list_users(db)
    if not users:
        raise HTTPException(status_code=404, detail="User not found")
    return users

@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = user_service.get_user(user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/by-username/{username}", response_model=UserResponse)
def get_user_by_username(username: str, db: Session = Depends(get_db)):
    user = user_service.get_user_by_username(username, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.post("/setup", response_model=bool)
def setup_user(req: UserSetupRequest, current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    user_service.setup_user(current_user, req, db)
    return True