import httpx
from fastapi import HTTPException
from sqlmodel import Session, select

from core.models import User, UserRole
from core.models.user import LoginType
from core.schemas.user_schema import UserCreateRequest
from core.services.user_service import create_user

GOOGLE_OAUTH_URL = "https://oauth2.googleapis.com/tokeninfo"


async def verify_google_token(id_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(GOOGLE_OAUTH_URL, params={"id_token": id_token})
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid Google token")
        return response.json()


async def authenticate_google_user(db_session: Session, id_token: str) -> User:
    user_info = await verify_google_token(id_token)

    email = user_info.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Google token missing email")

    # Check if user exists
    statement = select(User).where(User.email == email)
    user = db_session.exec(statement).first()

    # If user doesn't exist, create it (optional)
    if not user:
        user_create_req = UserCreateRequest(username=email, email=email, password='', role=UserRole.tutor,
                                            login_type=LoginType.google)
        user = create_user(user_create_req, db_session)

    return user
