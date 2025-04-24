from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session
from core.models.user import User
from core.schemas.user_schema import UserCreateRequest
from core.services import user_service
from core.configs.database import get_db

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=User)
def create_user(user_req: UserCreateRequest, db: Session = Depends(get_db)):
    return user_service.create_user(user_req, db)

@router.get("/{user_id}", response_model=User)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = user_service.get_user(user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/by-username/{username}", response_model=User)
def get_user_by_username(username: str, db: Session = Depends(get_db)):
    user = user_service.get_user_by_username(username, db)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user