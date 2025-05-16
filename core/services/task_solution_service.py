from typing import List, Optional, Dict, Any
from sqlmodel import Session, select

from core.configs import storage
from core.models.task_solution import TaskSolution
from datetime import datetime, UTC

from core.utils.utils import STORAGE_PRIVATE_BUCKET


def list_by_task(db: Session, task_id: int) -> List[TaskSolution]:
    statement = select(TaskSolution).where(TaskSolution.task_id == task_id)
    return db.exec(statement).all()


def __make_task_solution(solution: Optional[TaskSolution], include_files: bool) -> Optional[TaskSolution]:
    if not solution:
        return None
    if include_files and solution.files_path:
        # Download and attach test files content (add as a dynamic attribute)
        solution.files_content = storage.download_file(STORAGE_PRIVATE_BUCKET, solution.files_path)
    return solution


def get_by_id(db: Session, solution_id: int, include_files: bool = False) -> Optional[TaskSolution]:
    task = db.get(TaskSolution, solution_id)
    return __make_task_solution(task, include_files)


def get_by_userid_taskid(db: Session, user_id: int, task_id: int, include_files: bool = False) -> Optional[
    TaskSolution]:
    statement = select(TaskSolution).where(
        (TaskSolution.user_id == user_id) & (TaskSolution.task_id == task_id)
    )
    solution = db.exec(statement).first()
    return __make_task_solution(solution, include_files)


def create(
        db: Session,
        user_id: int,
        task_id: int,
        file_path: str | None,
        score: Optional[float] = None,
        scoring_version: Optional[str] = None,
        result: Dict[str, Any] = None,
) -> TaskSolution:
    solution = TaskSolution(
        user_id=user_id,
        task_id=task_id,
        date=datetime.now(UTC),
        file_path=file_path,
        score=score,
        scoring_version=scoring_version,
        status="created",
        result=result
    )
    db.add(solution)
    db.commit()
    db.refresh(solution)
    return solution


def update(
        db: Session,
        solution_id: int,
        score: Optional[float] = None,
        scoring_version: Optional[str] = None,
        status: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
) -> Optional[TaskSolution]:
    solution = db.get(TaskSolution, solution_id)
    if not solution:
        return None
    if score is not None:
        solution.score = score
    if scoring_version is not None:
        solution.scoring_version = scoring_version
    if status is not None:
        solution.status = status
    if result is not None:
        solution.result = result
    solution.last_updated = datetime.now(UTC)
    db.add(solution)
    db.commit()
    db.refresh(solution)
    return solution
