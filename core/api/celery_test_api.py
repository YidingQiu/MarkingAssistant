from fastapi import APIRouter, HTTPException
from celery.result import AsyncResult
from core.celery.app import celery_app
from core.celery.tasks.hello import hello_world, hello_progress, test_error_handling
from pydantic import BaseModel
from typing import Any, Dict

router = APIRouter(prefix="/celery", tags=["celery"])

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

class TaskResult(BaseModel):
    task_id: str
    status: str
    result: Any = None
    progress: Dict[str, Any] = None
    error: str = None

@router.post("/hello", response_model=TaskResponse)
async def start_hello_task(name: str = "World"):
    """Start a simple hello world task."""
    task = hello_world.delay(name)
    return TaskResponse(
        task_id=task.id,
        status="PENDING",
        message=f"Hello task started for {name}"
    )

@router.post("/hello-progress", response_model=TaskResponse)
async def start_hello_progress_task(name: str = "World", steps: int = 5):
    """Start a hello world task with progress tracking."""
    task = hello_progress.delay(name, steps)
    return TaskResponse(
        task_id=task.id,
        status="PENDING",
        message=f"Hello progress task started for {name} with {steps} steps"
    )

@router.post("/test-error", response_model=TaskResponse)
async def start_error_test_task(should_fail: bool = False):
    """Start an error handling test task."""
    task = test_error_handling.delay(should_fail)
    return TaskResponse(
        task_id=task.id,
        status="PENDING",
        message=f"Error test task started, should_fail: {should_fail}"
    )

@router.get("/status/{task_id}", response_model=TaskResult)
async def get_task_status(task_id: str):
    """Get the status of a Celery task."""
    try:
        result = AsyncResult(task_id, app=celery_app)
        
        if result.state == 'PENDING':
            response = TaskResult(
                task_id=task_id,
                status='PENDING',
                result=None
            )
        elif result.state == 'PROGRESS':
            response = TaskResult(
                task_id=task_id,
                status='PROGRESS',
                progress=result.info
            )
        elif result.state == 'SUCCESS':
            response = TaskResult(
                task_id=task_id,
                status='SUCCESS',
                result=result.result
            )
        elif result.state == 'FAILURE':
            response = TaskResult(
                task_id=task_id,
                status='FAILURE',
                error=str(result.info)
            )
        else:
            response = TaskResult(
                task_id=task_id,
                status=result.state,
                result=result.info
            )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Task not found: {str(e)}") 