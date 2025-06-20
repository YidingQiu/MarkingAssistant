import unittest
from pathlib import Path
import tempfile
import shutil
import os
import zipfile

# Add src to path to allow imports
import sys
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from marking_assistant.assignments.student import Student
from marking_assistant.assignments.submission import Submission
from marking_assistant.assignments.loaders import MoodleLoader

class TestStudent(unittest.TestCase):
    def test_student_creation(self):
        student = Student(id="z1234567", name="Test Student")
        self.assertEqual(student.id, "z1234567")
        self.assertEqual(student.name, "Test Student")

class TestSubmission(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.student = Student(id="z1234567", name="Test Student")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_discover_files(self):
        # Create some dummy files
        (Path(self.test_dir) / "problem1.py").touch()
        (Path(self.test_dir) / "problem2.ipynb").touch()
        (Path(self.test_dir) / "report.pdf").touch()
        (Path(self.test_dir) / "notes.txt").touch()
        (Path(self.test_dir) / "data.csv").touch() # Should not be picked up

        submission = Submission(self.student, self.test_dir)
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
        
        submission = Submission(self.student, self.test_dir)
        
        self.assertEqual(len(submission.files), 2)
        filenames = {p.name for p in submission.files}
        self.assertIn("solution.py", filenames)
        self.assertIn("raw.txt", filenames)
        self.assertFalse(zip_path.exists()) # Check if zip was deleted

class TestMoodleLoader(unittest.TestCase):
    def setUp(self):
        self.base_dir = Path(tempfile.mkdtemp())
        self.task_name = "Lab1"
        self.task_dir = self.base_dir / self.task_name
        self.task_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.base_dir)

    def test_get_submissions(self):
        # Create dummy submission folders
        (self.task_dir / "z1234567_Student One_assignsubmission_file_").mkdir()
        (self.task_dir / "z7654321_submission_Student Two_assignsubmission_file").mkdir()
        (self.task_dir / "not_a_submission").mkdir()
        
        loader = MoodleLoader(str(self.base_dir))
        submissions = loader.get_submissions_for_task(self.task_name)
        
        self.assertEqual(len(submissions), 2)
        student_names = {s.student.name for s in submissions}
        self.assertIn("Student One", student_names)
        self.assertIn("Student Two", student_names)
        
        student_ids = {s.student.id for s in submissions}
        self.assertIn("z1234567", student_ids)
        self.assertIn("z7654321", student_ids)

if __name__ == '__main__':
    unittest.main() 