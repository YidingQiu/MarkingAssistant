from fastapi import APIRouter, Depends, HTTPException
from typing import List
from sqlmodel import Session

from core.auth.auth_handler import get_current_user
from core.models.rubric_config import RubricConfig, RubricScope
from core.services import rubric_config_service
from core.configs.database import get_db

router = APIRouter(prefix="/rubric-config", tags=["rubric-config"])

@router.get("/{rubric_config_id}", response_model=RubricConfig)
def read_rubric_config(rubric_config_id: int, db: Session = Depends(get_db)):
    rubric = rubric_config_service.get_by_id(rubric_config_id, db)
    if not rubric:
        raise HTTPException(status_code=404, detail="Rubric config not found")
    return rubric

@router.get("/scope/{scope}", response_model=List[RubricConfig])
def list_rubric_configs(scope: RubricScope, db: Session = Depends(get_db)):
    return rubric_config_service.list_by_scope(scope, db)

@router.post("/", response_model=RubricConfig)
def create_rubric(value: dict, scope: RubricScope = RubricScope.public, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return rubric_config_service.create(db, value, scope)