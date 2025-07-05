import logging
import os
import zipfile
from pathlib import Path
from typing import List, Optional

from .student import Student

logger = logging.getLogger(__name__)


class Submission:
    """Represents a single student's submission for a task."""

    def __init__(self, student: Student, submission_path: str):
        self.student = student
        self.submission_path = Path(submission_path)
        self.files: List[Path] = []
        self._discover_files()

    def _discover_files(self) -> None:
        """
        Discovers relevant submission files, handling extraction of .zip archives.
        The original .zip file is deleted after successful extraction.
        """
        if not self.submission_path.is_dir():
            logger.error(f"Submission directory not found for student {self.student.id}: {self.submission_path}")
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
            logger.warning(f"No processable files found in {self.submission_path} for student {self.student.id}")
        else:
            logger.info(f"Discovered {len(self.files)} processable files for student {self.student.id}")

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

    def __repr__(self) -> str:
        return f"Submission(student={self.student.name}, path='{self.submission_path}')" 