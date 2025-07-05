from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session
from starlette.middleware.cors import CORSMiddleware

from core.api import user_api, course_api, task_api, solution_api, auth_api
from core.api import rubric_config_api
from core.auth.auth_handler import authenticate_user, create_access_token, get_current_user
from core.configs.database import init_db, get_db
from core.schemas.token import Token
from core.schemas.user_schema import UserResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

# Define allowed origins
origins = ["http://localhost:3000", "http://34.223.67.247:3000", "https://markmyworks.com"] # TODO: add our domain

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allowed origins
    allow_credentials=True,  # Allow cookies/auth headers
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

# Include routers
app.include_router(user_api.router)
app.include_router(rubric_config_api.router)
app.include_router(course_api.router)
app.include_router(task_api.router)
app.include_router(solution_api.router)
app.include_router(auth_api.router)

@app.get("/test", response_model=UserResponse)
def read_users_me(current_user=Depends(get_current_user)):
    return current_user