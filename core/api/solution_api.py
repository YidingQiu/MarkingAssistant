from fastapi import APIRouter, Depends, HTTPException, Query, Body
from typing import List, Optional, Dict, Any
from sqlmodel import Session

from core.auth.auth_handler import get_current_user
from core.configs.database import get_db
from core.configs.storage import make_upload_url
from core.services import task_solution_service, task_service
from core.models.task_solution import TaskSolution
from core.utils.utils import STORAGE_PRIVATE_BUCKET, make_solution_file_path

router = APIRouter(prefix="/solutions", tags=["solutions"])


@router.get("/by_task/{task_id}", response_model=List[TaskSolution])
def list_solutions_by_task(task_id: int, db: Session = Depends(get_db)):
    return task_solution_service.list_by_task(db, task_id)


@router.get("/{solution_id}", response_model=Optional[TaskSolution])
def get_solution_by_id(solution_id: int, include_files: bool = Query(False), db: Session = Depends(get_db)):
    solution = task_solution_service.get_by_id(db, solution_id, include_files)
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")
    return solution


@router.get("/by_user_task", response_model=Optional[TaskSolution])
def get_solution_by_user_task(user_id: int = Query(...), task_id: int = Query(...), include_files: bool = Query(False),
                              db: Session = Depends(get_db)):
    solution = task_solution_service.get_by_userid_taskid(db, user_id, task_id, include_files)
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")
    return solution


@router.post("/", response_model=Optional[TaskSolution])
def create_solution(
        user_id: Optional[int] = Body(None),
        task_id: int = Body(...),
        file_name: str = Body(...),
        db: Session = Depends(get_db)
):
    """
    user_id: None if bulk submitting solution
    """
    file_path = make_solution_file_path(task_id, task_id, user_id, file_name)

    if not user_id:
        ...  # todo send to celery for bulk process
        return None

    solution = task_solution_service.create(
        db=db,
        user_id=user_id,
        task_id=task_id,
        file_path=file_path,
    )
    return solution


# ## todo by tutor / by student
@router.put("/{solution_id}", response_model=Optional[TaskSolution])
def update_solution(
        solution_id: int,
        score: Optional[float] = Body(...),
        result: Optional[Dict[str, Any]] = None,
        db: Session = Depends(get_db)
):
    solution = task_solution_service.update(
        db=db,
        solution_id=solution_id,
        score=score,
        result=result
    )
    if not solution:
        raise HTTPException(status_code=404, detail="Solution not found")
    return solution


@router.post("/upload_link")
def create_upload_link(task_id: int = Query(...), user_id: Optional[str] = Query(None), file_name: str = Query(...),
                       db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """
    user_id: None if bulk uploading solution
    """
    task = task_service.get_task(db, task_id)
    path = make_solution_file_path(task.course_id, task_id, user_id, file_name)
    upload_link = make_upload_url(STORAGE_PRIVATE_BUCKET, path)
    return upload_link
