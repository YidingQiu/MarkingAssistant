import logging
import os
import re
import shutil
import subprocess
import sys
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest

from ..assignments.submission import Submission
from .quality_runner import CodeQualityRunner
from ..extractors.content_extractor import ContentExtractor

logger = logging.getLogger(__name__)


class TestRunner:
    """Orchestrates the running of tests for a student's submission."""

    def __init__(self, test_cases_dir: str, results_dir: str, task_name: str, timeout: int = 30):
        self.test_cases_dir = Path(test_cases_dir)
        self.results_dir = Path(results_dir)
        self.task_name = task_name
        self.timeout = timeout
        self.temp_dir: Optional[Path] = None

    def run_tests_for_submission(self, submission: Submission, install_packages: bool = True) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Sets up an environment and runs all tests and quality checks for a single submission.
        """
        self.temp_dir = self.results_dir.parent / 'temp' / self.task_name / f"{submission.student.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Overall results containers
        test_results_json = self._create_results_dict(submission, 'test_results')
        quality_results_json = self._create_results_dict(submission, 'quality_results')

        try:
            # 1. Setup Environment
            copied_files_map = self._setup_test_environment(submission)
            self._copy_test_data_files()
            
            # New step: Convert notebooks to Python files before any processing
            processed_files_map = self._convert_notebooks_to_py(copied_files_map)
            
            # Group all code content for dependency analysis
            all_code_content = ""
            for temp_path in processed_files_map.values():
                if temp_path.suffix == '.py':
                     all_code_content += temp_path.read_text(encoding='utf-8')

            if install_packages and all_code_content:
                self._install_dependencies(all_code_content)

            # 2. Process each file
            for original_path, temp_path in processed_files_map.items():
                problem_number = self._get_problem_number_from_filename(temp_path.name)
                if not problem_number:
                    logger.warning(f"Skipping file with no problem number: {temp_path.name}")
                    continue

                test_results_json['problems'][problem_number] = {'solution_path': str(original_path)}
                quality_results_json['problems'][problem_number] = {'solution_path': str(original_path)}

                # Run quality checks
                quality_results = CodeQualityRunner.run_all_checks(str(temp_path))
                quality_results_json['problems'][problem_number]['quality_results'] = quality_results

                # Run tests
                test_file = self._find_test_case_for_problem(problem_number)
                if test_file:
                    pytest_output = self._run_pytest_subprocess(test_file, str(temp_path))
                    test_results_json['problems'][problem_number]['test_results'] = pytest_output
                else:
                    logger.warning(f"No test case found for problem {problem_number}")
                    test_results_json['problems'][problem_number]['test_results'] = {'error': 'No test file found.'}

            # 3. Save results
            self._save_results(test_results_json, submission, "test_results")
            self._save_results(quality_results_json, submission, "quality_results")

        except Exception as e:
            logger.critical(f"Unhandled error in TestRunner for student {submission.student.id}: {e}", exc_info=True)
            # Save error state if something critical happened
            error_results = self._create_results_dict(submission, 'error')
            error_results['error'] = traceback.format_exc()
            self._save_results(error_results, submission, "error_results")

        finally:
            self._cleanup_test_environment()

        return test_results_json, quality_results_json

    def _create_results_dict(self, submission: Submission, result_type: str) -> Dict[str, Any]:
        """Creates a standard dictionary structure for results."""
        return {
            'metadata': {
                'student_name': submission.student.name,
                'student_id': submission.student.id,
                'task_name': self.task_name,
                'timestamp': datetime.now().isoformat(),
                'result_type': result_type
            },
            'problems': {}
        }

    def _setup_test_environment(self, submission: Submission) -> Dict[Path, Path]:
        """Creates a temporary directory and copies submission files."""
        if not self.temp_dir:
            raise ValueError("Temporary directory not set.")
            
        logger.info(f"Setting up test environment for {submission.student.id} in {self.temp_dir}")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        copied_files_map: Dict[Path, Path] = {}
        for file_path in submission.files:
            try:
                # Ensure we handle files that might be outside the immediate submission path if discovered
                relative_path = file_path.relative_to(submission.submission_path)
            except ValueError:
                relative_path = file_path.name # Fallback for files not in submission path (e.g., from zip)

            dest_path = self.temp_dir / relative_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, dest_path)
            copied_files_map[file_path] = dest_path

        return copied_files_map

    def _convert_notebooks_to_py(self, copied_files_map: Dict[Path, Path]) -> Dict[Path, Path]:
        """
        Converts any .ipynb files in the temp directory to .py files.
        Returns an updated map of original paths to their new, possibly converted, temp paths.
        """
        if not self.temp_dir:
            logger.error("Cannot convert notebooks, temporary directory is not set.")
            return copied_files_map

        processed_files_map: Dict[Path, Path] = {}
        for original_path, temp_path in copied_files_map.items():
            if temp_path.suffix == '.ipynb':
                logger.info(f"Converting notebook {temp_path.name} to a Python script for testing.")
                code = ContentExtractor.extract_code(temp_path)
                
                if code:
                    new_temp_path = temp_path.with_suffix('.py')
                    new_temp_path.write_text(code, encoding='utf-8')
                    temp_path.unlink()  # Remove the original .ipynb from temp dir
                    processed_files_map[original_path] = new_temp_path
                    logger.info(f"Successfully converted {temp_path.name} to {new_temp_path.name}")
                else:
                    logger.warning(f"Could not extract any code from {original_path.name}. It will be skipped.")
            else:
                processed_files_map[original_path] = temp_path
        
        return processed_files_map

    def _get_problem_number_from_filename(self, file_name: str) -> Optional[str]:
        """Extracts problem number from various file naming formats."""
        base_name = Path(file_name).stem
        match = re.search(r'(?:problem|q|question|task)[_\s]?(\d+[a-zA-Z]?)\b', base_name, re.IGNORECASE)
        if match:
            return match.group(1)
        match = re.search(r'(\d+[a-zA-Z]?)$', base_name)
        if match:
            return match.group(1)
        return None

    def _find_test_case_for_problem(self, problem_number: str) -> Optional[Path]:
        """Finds the test case file for a specific problem."""
        test_file = self.test_cases_dir / f'test_problem{problem_number}.py'
        if test_file.exists():
            return test_file
        logger.warning(f"Test case file not found: {test_file}")
        return None
    
    def _copy_test_data_files(self):
        """Copies non-test, non-python data files from the test_cases directory."""
        if not self.temp_dir: return
        for item in self.test_cases_dir.iterdir():
            if item.is_file() and not item.name.startswith('test_') and not item.name.endswith('.py'):
                shutil.copy2(item, self.temp_dir / item.name)
                logger.info(f"Copied data file: {item.name}")

    def _install_dependencies(self, code_content: str):
        """Installs required packages identified from the code."""
        if not self.temp_dir: return
        # A simple regex to find imports
        imports = set(re.findall(r'^(?:from|import)\s+([a-zA-Z0-9_\.]+)', code_content, re.MULTILINE))
        if not imports: return

        packages_to_install = {imp.split('.')[0] for imp in imports}
        
        # Filter out standard libraries and local modules
        std_libs = set(sys.stdlib_module_names)
        local_modules = {p.stem for p in self.temp_dir.glob('*.py')}
        packages_to_install -= std_libs
        packages_to_install -= local_modules

        if packages_to_install:
            logger.info(f"Attempting to install packages: {packages_to_install}")
            try:
                subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', *packages_to_install],
                    check=True, capture_output=True, text=True
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to install packages: {e.stderr}")

    def _run_pytest_subprocess(self, test_file: Path, student_solution_path: str) -> Dict[str, Any]:
        """Runs pytest in a subprocess and returns structured results."""
        env = os.environ.copy()
        env['STUDENT_SOLUTION_PATH'] = student_solution_path
        
        try:
            cmd = ['python', '-m', 'pytest', '-v', str(test_file)]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.timeout, env=env, check=False
            )
            
            # Basic parsing, can be made more robust
            stdout = result.stdout
            passed = result.returncode == pytest.ExitCode.OK
            summary_line = stdout.strip().split('\n')[-1]

            return {
                'summary': {
                    'passed': passed,
                    'exit_code': result.returncode,
                    'summary_line': summary_line
                },
                'details': {
                    'full_output': stdout,
                    'error_output': result.stderr
                }
            }

        except subprocess.TimeoutExpired:
            return {'summary': {'status': 'timeout'}, 'details': {}}
        except Exception as e:
            return {'summary': {'status': 'execution_error'}, 'details': {'error_output': str(e)}}

    def _save_results(self, data: Dict, submission: Submission, result_type: str):
        """Saves the results dictionary to a JSON file."""
        results_dir = self.results_dir / self.task_name
        results_dir.mkdir(parents=True, exist_ok=True)
        
        # Filename example: Student_Name_z1234567_Lab1_test_results.json
        safe_name = submission.student.name.replace(' ', '_')
        filename = f"{safe_name}_{submission.student.id}_{self.task_name}_{result_type}.json"
        file_path = results_dir / filename
        
        try:
            with file_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            logger.info(f"Saved {result_type} to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save {result_type} to {file_path}: {e}")

    def _cleanup_test_environment(self):
        """Removes the temporary test directory."""
        if self.temp_dir and self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                logger.info(f"Successfully cleaned up temporary directory: {self.temp_dir}")
            except Exception as e:
                logger.error(f"Failed to clean up temporary directory {self.temp_dir}: {e}")
        self.temp_dir = None 