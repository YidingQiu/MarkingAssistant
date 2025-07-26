import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import tempfile
import shutil
import os
import zipfile

# Add src to path to allow imports
import sys
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from core.models import User, Task, TaskSolution, UserRole
from marking_assistant.assignments.submission import Submission
from marking_assistant.assignments.loaders import MoodleLoader


class TestSubmission(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        # Create a mock User object
        self.user = User(
            id=1,
            username="z1234567",
            email="z1234567@student.unsw.edu.au",
            password="hashed_password",
            role=UserRole.student
        )

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_discover_files(self):
        # Create some dummy files
        (Path(self.test_dir) / "problem1.py").touch()
        (Path(self.test_dir) / "problem2.ipynb").touch()
        (Path(self.test_dir) / "report.pdf").touch()
        (Path(self.test_dir) / "notes.txt").touch()
        (Path(self.test_dir) / "data.csv").touch() # Should not be picked up

        submission = Submission(self.user, self.test_dir, submission_id=1)
        self.assertEqual(len(submission.files), 4)
        filenames = {p.name for p in submission.files}
        self.assertIn("problem1.py", filenames)
        self.assertIn("problem2.ipynb", filenames)
        self.assertIn("report.pdf", filenames)
        self.assertIn("notes.txt", filenames)
        self.assertNotIn("data.csv", filenames)

    def test_zip_extraction(self):
        zip_path = Path(self.test_dir) / "submission.zip"
        with zipfile.ZipFile(zip_path, 'w') as zf:
            zf.writestr("solution.py", "print('hello')")
            zf.writestr("data/raw.txt", "some data")
        
        submission = Submission(self.user, self.test_dir, submission_id=1)
        
        self.assertEqual(len(submission.files), 2)
        filenames = {p.name for p in submission.files}
        self.assertIn("solution.py", filenames)
        self.assertIn("raw.txt", filenames)
        self.assertFalse(zip_path.exists()) # Check if zip was deleted

    def test_backward_compatibility_student_property(self):
        submission = Submission(self.user, self.test_dir, submission_id=1)
        # Test that the student property returns the user for backward compatibility
        self.assertEqual(submission.student, self.user)
        self.assertEqual(submission.student.username, "z1234567")

    def test_get_user_info(self):
        submission = Submission(self.user, self.test_dir, submission_id=1)
        user_info = submission.get_user_info()
        
        self.assertEqual(user_info['id'], "z1234567")
        self.assertEqual(user_info['email'], "z1234567@student.unsw.edu.au")
        self.assertEqual(user_info['role'], UserRole.student)
        self.assertEqual(user_info['database_id'], 1)


class TestMoodleLoader(unittest.TestCase):
    def setUp(self):
        self.base_dir = Path(tempfile.mkdtemp())
        self.task_name = "Lab1"
        self.task_dir = self.base_dir / self.task_name
        self.task_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.base_dir)

    @patch('marking_assistant.assignments.loaders.get_db')
    def test_get_submissions_with_mocked_db(self, mock_get_db):
        # Create dummy submission folders
        (self.task_dir / "z1234567_Student One_assignsubmission_file_").mkdir()
        (self.task_dir / "z7654321_submission_Student Two_assignsubmission_file").mkdir()
        (self.task_dir / "not_a_submission").mkdir()
        
        # Mock database session and objects
        mock_session = MagicMock()
        mock_get_db.return_value = iter([mock_session])
        
        # Mock task
        mock_task = Task(
            id=1,
            name=self.task_name,
            description="Test task",
            course_id=1,
            scoring_config={}
        )
        
        # Mock users
        mock_user1 = User(
            id=1,
            username="z1234567",
            email="z1234567@student.unsw.edu.au",
            password="hashed_password",
            role=UserRole.student
        )
        mock_user2 = User(
            id=2,
            username="z7654321", 
            email="z7654321@student.unsw.edu.au",
            password="hashed_password",
            role=UserRole.student
        )
        
        # Mock submissions
        mock_submission1 = TaskSolution(
            id=1,
            user_id=1,
            task_id=1,
            file_path=str(self.task_dir / "z1234567_Student One_assignsubmission_file_"),
            status="submitted"
        )
        mock_submission2 = TaskSolution(
            id=2,
            user_id=2,
            task_id=1,
            file_path=str(self.task_dir / "z7654321_submission_Student Two_assignsubmission_file"),
            status="submitted"
        )
        
        # Configure session mock behavior
        def mock_exec_side_effect(statement):
            mock_result = MagicMock()
            # Check what type of query it is by inspecting the statement
            if hasattr(statement, 'where_criteria') or 'Task' in str(statement):
                if 'Task' in str(statement):
                    mock_result.first.return_value = mock_task
                elif 'z1234567' in str(statement):
                    mock_result.first.return_value = mock_user1
                elif 'z7654321' in str(statement):
                    mock_result.first.return_value = mock_user2
                else:
                    mock_result.first.return_value = None
            return mock_result
        
        mock_session.exec.side_effect = mock_exec_side_effect
        mock_session.add = MagicMock()
        mock_session.commit = MagicMock()
        mock_session.refresh = MagicMock()
        mock_session.rollback = MagicMock()
        mock_session.close = MagicMock()
        
        # Set up refresh side effects to simulate database ID assignment
        def refresh_side_effect(obj):
            if isinstance(obj, Task) and not obj.id:
                obj.id = 1
            elif isinstance(obj, User) and not obj.id:
                obj.id = 1 if obj.username == "z1234567" else 2
            elif isinstance(obj, TaskSolution) and not obj.id:
                obj.id = 1 if obj.user_id == 1 else 2
        
        mock_session.refresh.side_effect = refresh_side_effect
        
        loader = MoodleLoader(str(self.base_dir))
        submissions = loader.get_submissions_for_task(self.task_name)
        
        # Verify results
        self.assertEqual(len(submissions), 2)
        
        # Check that users were created/retrieved correctly
        usernames = {s.user.username for s in submissions}
        self.assertIn("z1234567", usernames)
        self.assertIn("z7654321", usernames)
        
        # Check that submission objects have the right properties
        for submission in submissions:
            self.assertIsInstance(submission.user, User)
            self.assertIsNotNone(submission.submission_id)
            self.assertIsInstance(submission.submission_path, Path)

    def test_extract_user_info(self):
        # Test the static method for extracting user info from folder names
        test_cases = [
            ("z1234567_Student One_assignsubmission_file_", ("z1234567", "Student One")),
            ("z7654321_submission_Student Two_assignsubmission_file", ("z7654321", "Student Two")),
            ("invalid_folder_name", (None, None)),
            ("z9999999_John_Doe_assignsubmission_file_", ("z9999999", "John Doe")),
        ]
        
        for folder_name, expected in test_cases:
            with self.subTest(folder_name=folder_name):
                result = MoodleLoader._extract_user_info(folder_name)
                self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main() 