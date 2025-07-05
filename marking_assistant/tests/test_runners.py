import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import shutil
import os

import sys
sys.path.append(str(Path(__file__).parent.parent / 'src'))

from marking_assistant.runners.quality_runner import CodeQualityRunner
from marking_assistant.runners.test_runner import TestRunner
from marking_assistant.assignments.student import Student
from marking_assistant.assignments.submission import Submission

class TestCodeQualityRunner(unittest.TestCase):

    @patch('subprocess.run')
    def test_run_flake8_with_issues(self, mock_subprocess_run):
        # Mock the subprocess to return a failing run
        mock_result = MagicMock()
        mock_result.stdout = "file.py:1:1: F401 'os' imported but unused"
        mock_result.stderr = ""
        mock_subprocess_run.return_value = mock_result

        result = CodeQualityRunner.run_flake8('dummy/file.py')
        self.assertTrue(result['has_issues'])
        self.assertIn("F401", result['output'])

    @patch('subprocess.run')
    def test_run_black_with_issues(self, mock_subprocess_run):
        # Mock the subprocess to return a failing run (needs reformatting)
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "1 file would be reformatted."
        mock_subprocess_run.return_value = mock_result
        
        result = CodeQualityRunner.run_black('dummy/file.py')
        self.assertTrue(result['has_issues'])
        self.assertIn("reformatted", result['output'])

class TestTestRunner(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp())
        self.results_dir = self.test_dir / "results"
        self.test_cases_dir = self.test_dir / "test_cases"
        self.task_name = "Lab1"
        (self.test_cases_dir / self.task_name).mkdir(parents=True)

        self.student = Student("z123", "tester")
        submission_path = self.test_dir / "submission"
        submission_path.mkdir()
        (submission_path / "problem1.py").write_text("print('hello')")
        self.submission = Submission(self.student, str(submission_path))

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch('marking_assistant.runners.test_runner.TestRunner._run_pytest_subprocess')
    @patch('marking_assistant.runners.quality_runner.CodeQualityRunner.run_all_checks')
    def test_run_tests_for_submission(self, mock_quality_checks, mock_run_pytest):
        # Mock the runners to avoid actual subprocess calls
        mock_quality_checks.return_value = {"flake8": {"has_issues": False}, "black": {"has_issues": False}}
        mock_run_pytest.return_value = {"summary": {"passed": True}}

        # Create a dummy test case file so it can be found
        (self.test_cases_dir / self.task_name / "test_problem1.py").touch()
        
        runner = TestRunner(
            test_cases_dir=str(self.test_cases_dir / self.task_name),
            results_dir=str(self.results_dir),
            task_name=self.task_name
        )
        
        test_results, quality_results = runner.run_tests_for_submission(self.submission)

        # Verify that the results files were created (mocked run, but files should be saved)
        results_path = self.results_dir / self.task_name
        student_file_prefix = f"{self.student.name}_{self.student.id}_{self.task_name}"
        self.assertTrue((results_path / f"{student_file_prefix}_test_results.json").exists())
        self.assertTrue((results_path / f"{student_file_prefix}_quality_results.json").exists())

        # Check that the mocked functions were called
        mock_quality_checks.assert_called_once()
        mock_run_pytest.assert_called_once()

        # Check content of returned dict
        self.assertIn("1", test_results["problems"])
        self.assertTrue(test_results["problems"]["1"]["test_results"]["summary"]["passed"])

if __name__ == '__main__':
    unittest.main() 