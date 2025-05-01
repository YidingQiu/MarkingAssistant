from typing import List, Optional

from fastapi import Depends
from sqlmodel import Session, select

from core.configs.database import get_db
from core.models.rubric_config import RubricConfig, RubricScope

def get_rubric_config_by_id(rubric_config_id: int, db: Session = Depends(get_db)) -> Optional[RubricConfig]:
    return db.get(RubricConfig, rubric_config_id)

def list_rubric_configs_by_scope(scope: RubricScope, db: Session = Depends(get_db)) -> List[RubricConfig]:
    statement = select(RubricConfig).where(RubricConfig.scope == scope)
    return db.exec(statement).all()

def create_rubric_config(value: dict, scope: RubricScope = RubricScope.public, db: Session = Depends(get_db)) -> RubricConfig:
    rubric_config = RubricConfig(value=value, scope=scope)
    db.add(rubric_config)
    db.commit()
    db.refresh(rubric_config)
    return rubric_config