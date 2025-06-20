import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

from .student import Student
from .submission import Submission

logger = logging.getLogger(__name__)


class MoodleLoader:
    """Loads student submissions from a Moodle-like folder structure."""

    def __init__(self, base_submissions_dir: str):
        self.base_dir = Path(base_submissions_dir)

    def get_submissions_for_task(self, task_name: str) -> List[Submission]:
        """
        Identifies and loads all student submissions for a specific task.
        """
        submissions: List[Submission] = []
        task_folder_path = self.base_dir / task_name

        if not task_folder_path.is_dir():
            logger.warning(f"Task folder not found: {task_folder_path}")
            return submissions

        for user_folder in task_folder_path.iterdir():
            if user_folder.is_dir() and 'submission' in user_folder.name.lower():
                student = self._parse_student_from_folder(user_folder.name)
                if student:
                    submission = Submission(student, str(user_folder))
                    submissions.append(submission)

        if not submissions:
            logger.warning(f"No user submissions found for task '{task_name}' in {task_folder_path}")

        return submissions

    def _parse_student_from_folder(self, folder_name: str) -> Optional[Student]:
        """
        Parses the user ID and name from a Moodle-style submission folder name.
        """
        user_id, user_name = self._extract_user_info(folder_name)
        if user_id and user_name:
            return Student(id=user_id, name=user_name)

        logger.warning(f"Could not parse user ID/name from folder: {folder_name}")
        return None

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