import logging
import os
import zipfile
from pathlib import Path
from typing import List, Optional

# Import User model from core instead of local Student
from core.models import User

logger = logging.getLogger(__name__)


class Submission:
    """Represents a single student's submission for a task."""

    def __init__(self, user: User, submission_path: str, submission_id: Optional[int] = None):
        self.user = user  # Changed from student to user
        self.submission_id = submission_id  # Database ID for the submission record
        self.submission_path = Path(submission_path)
        self.files: List[Path] = []
        self._discover_files()

    @property
    def student(self) -> User:
        """Backward compatibility property to access user as student."""
        return self.user

    def _discover_files(self) -> None:
        """
        Discovers relevant submission files, handling extraction of .zip archives.
        The original .zip file is deleted after successful extraction.
        """
        if not self.submission_path.is_dir():
            logger.error(f"Submission directory not found for user {self.user.username}: {self.submission_path}")
            return

        # First, handle any zip files by extracting them
        zip_files = list(self.submission_path.rglob('*.zip'))
        for zip_file_path in zip_files:
            self._extract_zip(zip_file_path)

        # Now, glob for processable files
        for ext in ('*.py', '*.ipynb', '*.pdf', '*.docx', '*.doc', '*.txt'):
            for file_path in self.submission_path.rglob(ext):
                if self._is_valid_file(file_path):
                    self.files.append(file_path.resolve())
        
        if not self.files:
            logger.warning(f"No processable files found in {self.submission_path} for user {self.user.username}")
        else:
            logger.info(f"Discovered {len(self.files)} processable files for user {self.user.username}")

    def _extract_zip(self, zip_file_path: Path) -> None:
        """Extracts a zip file and then deletes it."""
        try:
            logger.info(f"Found zip file: {zip_file_path}. Attempting to extract...")
            extract_to_path = zip_file_path.parent
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to_path)
            logger.info(f"Successfully extracted {zip_file_path} to {extract_to_path}")

            # After successful extraction, delete the zip file
            try:
                os.remove(zip_file_path)
                logger.info(f"Successfully deleted zip file: {zip_file_path}")
            except OSError as e:
                logger.error(f"Error deleting zip file {zip_file_path} after extraction: {e}")
        except zipfile.BadZipFile:
            logger.error(f"Error: {zip_file_path} is a bad zip file. Skipping.")
        except Exception as e:
            logger.error(f"Error extracting {zip_file_path}: {e}")

    @staticmethod
    def _is_valid_file(file_path: Path) -> bool:
        """Checks if a file is a valid submission file and not in an excluded directory."""
        if not file_path.is_file():
            return False
        
        path_str = str(file_path)
        excluded_dirs = ["__MACOSX", ".ipynb_checkpoints"]
        if any(excluded in path_str for excluded in excluded_dirs):
            return False
            
        return True

    def get_user_info(self) -> dict:
        """Get user information as a dictionary for compatibility."""
        return {
            'id': self.user.username,  # Use username as ID for compatibility
            'name': self.user.username,  # We might not have full name, use username
            'email': self.user.email,
            'role': self.user.role,
            'database_id': self.user.id  # Include database ID
        }

    def __repr__(self) -> str:
        return f"Submission(user={self.user.username}, path='{self.submission_path}', db_id={self.submission_id})" 