from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from core.api import user_api, course_api, task_api
from core.api import rubric_config_api
from core.configs.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

# Define allowed origins
origins = ["http://localhost:3000"] # TODO: add our domain

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