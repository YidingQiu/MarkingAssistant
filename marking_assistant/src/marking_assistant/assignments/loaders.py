import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple
from datetime import datetime
from sqlmodel import Session, select

# Core database imports
from core.models import User, Task, TaskSolution, UserRole
from core.services import user_service, task_service, task_solution_service
from core.configs.database import get_db

from .submission import Submission

logger = logging.getLogger(__name__)


class MoodleLoader:
    """Loads student submissions from a Moodle-like folder structure and integrates with database."""

    def __init__(self, base_submissions_dir: str, db_session: Optional[Session] = None):
        self.base_dir = Path(base_submissions_dir)
        self.db_session = db_session

    def get_submissions_for_task(self, task_name: str) -> List[Submission]:
        """
        Identifies and loads all student submissions for a specific task.
        Creates/updates database records for users, tasks, and submissions.
        """
        submissions: List[Submission] = []
        task_folder_path = self.base_dir / task_name

        if not task_folder_path.is_dir():
            logger.warning(f"Task folder not found: {task_folder_path}")
            return submissions

        # Get or create database session
        if self.db_session is None:
            db_gen = get_db()
            db_session = next(db_gen)
        else:
            db_session = self.db_session

        try:
            # Get or create task in database
            task = self._get_or_create_task(db_session, task_name)
            
            for user_folder in task_folder_path.iterdir():
                if user_folder.is_dir() and 'submission' in user_folder.name.lower():
                    user_id, user_name = self._extract_user_info(user_folder.name)
                    
                    if user_id and user_name:
                        # Get or create user in database
                        user = self._get_or_create_user(db_session, user_id, user_name)
                        
                        # Create submission record in database
                        submission_record = self._create_submission_record(
                            db_session, user, task, str(user_folder)
                        )
                        
                        # Create local Submission object for processing
                        submission = Submission(user, str(user_folder), submission_record.id)
                        submissions.append(submission)
                    else:
                        logger.warning(f"Could not parse user info from folder: {user_folder.name}")

            if not submissions:
                logger.warning(f"No user submissions found for task '{task_name}' in {task_folder_path}")

        except Exception as e:
            logger.error(f"Error processing submissions for task '{task_name}': {e}")
            db_session.rollback()
        finally:
            if self.db_session is None:
                db_session.close()

        return submissions

    def _get_or_create_task(self, db_session: Session, task_name: str) -> Task:
        """Get existing task or create new one in database."""
        try:
            # Try to find existing task by name
            statement = select(Task).where(Task.name == task_name)
            existing_task = db_session.exec(statement).first()
            
            if existing_task:
                logger.info(f"Found existing task: {task_name}")
                return existing_task
            
            # Create new task
            logger.info(f"Creating new task: {task_name}")
            task = Task(
                name=task_name,
                description=f"Task created from Moodle submission folder: {task_name}",
                course_id=1,  # Default course, should be configurable
                scoring_config={"default_config": True}
            )
            db_session.add(task)
            db_session.commit()
            db_session.refresh(task)
            return task
            
        except Exception as e:
            logger.error(f"Error creating/retrieving task '{task_name}': {e}")
            db_session.rollback()
            raise

    def _get_or_create_user(self, db_session: Session, user_id: str, user_name: str) -> User:
        """Get existing user or create new one in database."""
        try:
            # Try to find existing user by username (using student ID as username)
            statement = select(User).where(User.username == user_id)
            existing_user = db_session.exec(statement).first()
            
            if existing_user:
                logger.debug(f"Found existing user: {user_id}")
                return existing_user
            
            # Create new user
            logger.info(f"Creating new user: {user_id} - {user_name}")
            
            # Generate email from student ID if not provided
            email = f"{user_id}@student.unsw.edu.au"  # Default email format
            
            user = User(
                username=user_id,
                email=email,
                password="temp_password",  # Should be properly handled
                role=UserRole.student
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
            return user
            
        except Exception as e:
            logger.error(f"Error creating/retrieving user '{user_id}': {e}")
            db_session.rollback()
            raise

    def _create_submission_record(self, db_session: Session, user: User, task: Task, submission_path: str) -> TaskSolution:
        """Create a submission record in the database."""
        try:
            # Check if submission already exists
            statement = select(TaskSolution).where(
                TaskSolution.user_id == user.id,
                TaskSolution.task_id == task.id
            )
            existing_submission = db_session.exec(statement).first()
            
            if existing_submission:
                logger.info(f"Found existing submission for user {user.username} and task {task.name}")
                # Update submission path if needed
                if existing_submission.file_path != submission_path:
                    existing_submission.file_path = submission_path
                    existing_submission.last_updated = datetime.utcnow()
                    db_session.commit()
                    db_session.refresh(existing_submission)
                return existing_submission
            
            # Create new submission
            logger.info(f"Creating new submission for user {user.username} and task {task.name}")
            
            submission = TaskSolution(
                user_id=user.id,
                task_id=task.id,
                file_path=submission_path,
                status="submitted",
                date=datetime.utcnow()
            )
            db_session.add(submission)
            db_session.commit()
            db_session.refresh(submission)
            return submission
            
        except Exception as e:
            logger.error(f"Error creating submission record: {e}")
            db_session.rollback()
            raise

    @staticmethod
    def _extract_user_info(folder_name: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extracts user ID and name from a folder name.

        Expected format examples:
        - z1234567_Student Name_assignsubmission_file_
        - z1234567_submission_Student Name__assignsubmission_file
        """
        parts = folder_name.split('_assignsubmission_file', 1)[0]

        id_part: Optional[str] = None
        name_part: Optional[str] = None

        if '_submission_' in parts:
            id_part, name_part = parts.split('_submission_', 1)
        elif '_' in parts:
            potential_id, potential_name = parts.split('_', 1)
            if potential_id.startswith('z') and potential_id[1:].isdigit():
                id_part = potential_id
                name_part = potential_name

        if not (id_part and name_part):
            return None, None

        user_id = id_part if id_part.startswith('z') else None
        user_name = name_part.replace('_', ' ').strip() if name_part else None

        return user_id, user_name

    def get_submission_by_id(self, submission_id: int, db_session: Optional[Session] = None) -> Optional[Submission]:
        """Retrieve a submission by its database ID."""
        if db_session is None:
            db_gen = get_db()
            db_session = next(db_gen)
        
        try:
            submission_record = db_session.get(TaskSolution, submission_id)
            if not submission_record:
                return None
            
            # Get user information
            user = db_session.get(User, submission_record.user_id)
            if not user:
                logger.error(f"User not found for submission {submission_id}")
                return None
            
            # Create local Submission object
            submission = Submission(user, submission_record.file_path, submission_record.id)
            return submission
            
        except Exception as e:
            logger.error(f"Error retrieving submission {submission_id}: {e}")
            return None
        finally:
            if db_session != self.db_session:
                db_session.close()

    def get_submissions_for_user_and_task(self, user_id: str, task_name: str, db_session: Optional[Session] = None) -> List[Submission]:
        """Get all submissions for a specific user and task."""
        if db_session is None:
            db_gen = get_db()
            db_session = next(db_gen)
        
        try:
            # Get user and task
            user_stmt = select(User).where(User.username == user_id)
            user = db_session.exec(user_stmt).first()
            
            task_stmt = select(Task).where(Task.name == task_name)
            task = db_session.exec(task_stmt).first()
            
            if not user or not task:
                logger.warning(f"User {user_id} or task {task_name} not found")
                return []
            
            # Get submissions
            submission_stmt = select(TaskSolution).where(
                TaskSolution.user_id == user.id,
                TaskSolution.task_id == task.id
            )
            submission_records = db_session.exec(submission_stmt).all()
            
            submissions = []
            for record in submission_records:
                submission = Submission(user, record.file_path, record.id)
                submissions.append(submission)
            
            return submissions
            
        except Exception as e:
            logger.error(f"Error retrieving submissions for user {user_id} and task {task_name}: {e}")
            return []
        finally:
            if db_session != self.db_session:
                db_session.close() 