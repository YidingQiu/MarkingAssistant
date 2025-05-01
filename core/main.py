from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.api import user_api
from core.api import rubric_config_api
from core.configs.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

# Include routers
app.include_router(user_api.router)
app.include_router(rubric_config_api.router)