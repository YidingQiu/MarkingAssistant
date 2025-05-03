from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from sqlmodel import Session
from core.models.task import Task
from core.services import task_service
from core.configs.database import get_db

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.post("/", response_model=Task)
def create_task(
    name: str,
    description: Optional[str] = None,
    course_id: int = Query(...),
    test_files_url: Optional[str] = None,
    scoring_config: Dict[str, Any] = Query(...),
    rubric_config_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    return task_service.create_task(
        db=db,
        name=name,
        description=description,
        course_id=course_id,
        test_files_url=test_files_url,
        scoring_config=scoring_config,
        rubric_config_id=rubric_config_id
    )

@router.get("/{task_id}", response_model=Task)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = task_service.get_task(db, task_id, False)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.get("/by-course/{course_id}", response_model=List[Task])
def list_tasks_by_course_id(course_id: int, db: Session = Depends(get_db)):
    return task_service.list_tasks_by_course_id(db, course_id)

@router.put("/{task_id}", response_model=Task)
def update_task(task_id: int, update_data: Dict[str, Any], db: Session = Depends(get_db)):
    task = task_service.update_task(db, task_id, update_data)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found for update")
    return task