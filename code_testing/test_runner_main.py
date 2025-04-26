import os
import pytest
import json
import re
import logging
import subprocess  # Added for running pytest in subprocess
from datetime import datetime
from assignment_marker.moodle_loader import get_student_list
from assignment_marker.student_code_extractor import extract_code_from_files
from code_testing.quality_runner_main import run_quality_checks
import io
from contextlib import redirect_stdout, redirect_stderr
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('test_runner.log')
    ]
)
logger = logging.getLogger(__name__)

def get_lab_and_problem_info(lab_folder):
    """Extract lab number from the submission folder name."""
    # Example format: ZEIT1307-5254_00067_Lab 1_submission
    parts = lab_folder.split('_')
    lab_info = next(part for part in parts if 'Lab' in part)
    lab_number = lab_info.replace('Lab ', '')
    return lab_number

def find_test_cases(rubric_dir, problem_number, lab_number):
    """Find test cases for a specific problem in the rubric directory."""
    test_file = os.path.join(rubric_dir, 'test_cases', f'Lab{lab_number}', f'test_problem{problem_number}.py')
    if os.path.exists(test_file):
        return test_file
    return None

def run_pytest(test_file, student_solution_path, timeout=30):
    """Run pytest in a subprocess with a timeout and return results."""
    os.environ['STUDENT_SOLUTION_PATH'] = student_solution_path

    summary = {
        'passed': False,
        'exit_code': 'Timeout',
        'total_tests': 0,
        'passed_tests': 0,
        'failed_tests': 0,
        'status': 'timeout'
    }
    details = {
        'test_cases': [],
        'full_output': f"Test execution timed out after {timeout} seconds.",
        'error_output': None
    }

    try:
        # Run pytest using subprocess
        cmd = ['python', '-m', 'pytest', '-v', test_file]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=os.environ, # Pass environment variables
            check=False # Don't raise exception on non-zero exit code
        )

        stdout = result.stdout.replace('\r\n', '\n').replace('\r', '\n')
        stderr = result.stderr.replace('\r\n', '\n').replace('\r', '\n')
        exit_code = result.returncode

        # Parse output for summary details
        passed = exit_code == pytest.ExitCode.OK
        summary['passed'] = passed
        summary['exit_code'] = str(exit_code)
        summary['status'] = 'completed' # Override timeout status

        # Extract test cases details from stdout
        test_cases = []
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        lines = stdout.split('\n')
        summary_line = next((line for line in reversed(lines) if 'failed' in line or 'passed' in line or 'error' in line), None)
        
        for line in lines:
            if '::test_' in line and ('PASSED' in line or 'FAILED' in line or 'ERROR' in line):
                test_cases.append(line.strip())
                total_tests += 1
                if 'PASSED' in line:
                    passed_tests += 1
                elif 'FAILED' in line or 'ERROR' in line:
                    failed_tests += 1

        # Fallback parsing if the simple line check fails (e.g., summary line parsing)
        if total_tests == 0 and summary_line:
             match = re.search(r'(\d+) passed', summary_line)
             if match: passed_tests = int(match.group(1))
             match = re.search(r'(\d+) failed', summary_line)
             if match: failed_tests = int(match.group(1))
             # Count errors as failures for simplicity here
             match = re.search(r'(\d+) error', summary_line)
             if match: failed_tests += int(match.group(1))
             total_tests = passed_tests + failed_tests

        summary['total_tests'] = total_tests
        summary['passed_tests'] = passed_tests
        summary['failed_tests'] = failed_tests

        details['test_cases'] = test_cases
        details['full_output'] = stdout
        details['error_output'] = stderr if stderr else None

    except subprocess.TimeoutExpired as e:
        logger.warning(f"Pytest execution timed out for {test_file} after {timeout} seconds.")
        # summary and details are already set for timeout
        if e.stdout:
            details['full_output'] += "\nPartial Output before Timeout:\n" + e.stdout.replace('\r\n', '\n').replace('\r', '\n')
        if e.stderr:
             details['error_output'] = "Partial Error Output before Timeout:\n" + e.stderr.replace('\r\n', '\n').replace('\r', '\n')
            
    except Exception as e:
        logger.error(f"Error running pytest for {test_file}: {str(e)}")
        summary['passed'] = False
        summary['exit_code'] = 'Error'
        summary['status'] = 'execution_error'
        details['full_output'] = f"Internal error during test execution: {str(e)}"
        details['error_output'] = traceback.format_exc() # Include traceback for debugging

    # Return structured results consistent with the later processing
    return {
        'summary': summary,
        'details': details
    }

def get_problem_number(file_name):
    """Extract problem number from various file naming formats."""
    # Remove extension
    base_name = os.path.splitext(file_name)[0]

    # Try common patterns like Problem1, problem_1, q1, task1, etc.
    # Looks for (keyword)(separator)(number)(optional letter)
    # Keywords: problem, q, question, task
    # Separator: underscore, space, or none
    # Number: one or more digits
    # Letter: optional single letter (a-z)
    match = re.search(r'(?:problem|q|question|task)[_\s]?(\d+[a-zA-Z]?)\b', base_name, re.IGNORECASE)
    if match:
        return match.group(1)

    # If no keyword pattern, try finding a number (potentially with a letter) at the end of the filename
    # e.g., exercise1a.py -> 1a
    match = re.search(r'(\d+[a-zA-Z]?)$', base_name, re.IGNORECASE)
    if match:
        return match.group(1)

    # If still no match, try finding a number at the beginning
    # e.g., 1_solution.py -> 1
    match = re.search(r'^(\d+)', base_name)
    if match:
        return match.group(1)

    # Add a log message if no number is found
    logger.warning(f"Could not extract problem number from filename: {file_name}")
    return None

def save_json_results(data, base_dir, lab_number, student_name, student_id, result_type="results"):
    """Saves the provided data dictionary to a JSON file."""
    lab_results_dir = os.path.join(base_dir, f'Lab{lab_number}')
    os.makedirs(lab_results_dir, exist_ok=True)
    
    result_filename = f"{student_name}_{student_id}_Lab{lab_number}_{result_type}.json"
    result_path = os.path.join(lab_results_dir, result_filename)
    
    try:
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info(f"Successfully saved {result_type} to {result_path}")
    except Exception as e:
        logger.error(f"Failed to save {result_type} to {result_path}: {str(e)}")

def run_tests_for_student(student_info, submission_folder, rubric_dir, base_results_dir, test_timeout=30):
    """Run tests and quality checks for a student, saving results separately."""
    student_id = student_info['id']
    student_name = student_info['name']
    lab_folder = student_info['lab_folder']
    lab_number = get_lab_and_problem_info(lab_folder)
    
    # Construct the full path to the student's submission folder
    lab_folder_path = os.path.join(submission_folder, lab_folder)
    student_folder = None
    
    # Find the student's specific submission folder within the lab folder
    for folder in os.listdir(lab_folder_path):
        if student_id in folder and student_name.replace(' ', '') in folder.replace(' ', ''):
            student_folder = os.path.join(lab_folder_path, folder)
            break
    
    if not student_folder:
        logger.error(f"Could not find submission folder for student {student_name} ({student_id})")
        return
    
    # Define specific result directories
    test_results_dir = os.path.join(base_results_dir, 'test_results')
    flake8_results_dir = os.path.join(base_results_dir, 'flake8_result')
    black_results_dir = os.path.join(base_results_dir, 'black_result')
    temp_dir = os.path.join(base_results_dir, 'temp') # Keep temp dir within base results
    
    # Create directories if they don't exist
    os.makedirs(test_results_dir, exist_ok=True)
    os.makedirs(flake8_results_dir, exist_ok=True)
    os.makedirs(black_results_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)

    # Initialize results containers
    test_run_results = {
        'metadata': {
            'student_name': student_name,
            'student_id': student_id,
            'lab_number': lab_number,
            'timestamp': datetime.now().isoformat(),
        },
        'problems': {}
    }
    flake8_run_results = {
        'metadata': {
            'student_name': student_name,
            'student_id': student_id,
            'lab_number': lab_number,
            'timestamp': datetime.now().isoformat(),
        },
        'problems': {}
    }
    black_run_results = {
         'metadata': {
            'student_name': student_name,
            'student_id': student_id,
            'lab_number': lab_number,
            'timestamp': datetime.now().isoformat(),
        },
        'problems': {}
    }

    # Find all Python files in student's submission
    python_files = []
    for root, _, files in os.walk(student_folder):
        for file in files:
            # Only include .py files and exclude .fprg files
            if file.endswith('.py'):
                problem_number = get_problem_number(file)
                if problem_number:
                    python_files.append((os.path.join(root, file), problem_number))
    
    if not python_files:
        logger.warning(f"No valid Python files found for student {student_name} ({student_id})")
        return
        
    # Process each Python file found
    for file_path, problem_number in python_files:
        test_file = find_test_cases(rubric_dir, problem_number, lab_number)
        
        # Initialize problem entries in results dictionaries
        test_run_results['problems'][problem_number] = {'solution_path': file_path, 'test_results': None}
        flake8_run_results['problems'][problem_number] = {'solution_path': file_path, 'flake8_results': None}
        black_run_results['problems'][problem_number] = {'solution_path': file_path, 'black_results': None}
        
        temp_file = None # Ensure temp_file is defined for cleanup
        
        try:
            # Extract code for this specific file
            student_code = extract_code_from_files([file_path])
            
            if not student_code:
                logger.error(f"Could not read file {file_path}")
                test_run_results['problems'][problem_number]['error'] = "Could not read file"
                flake8_run_results['problems'][problem_number]['error'] = "Could not read file"
                black_run_results['problems'][problem_number]['error'] = "Could not read file"
                continue
            
            # Create temporary file with student's code
            temp_file = os.path.join(temp_dir, f'{student_id}_problem{problem_number}.py') # Unique temp file name
            
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(student_code[file_path])
            
            # --- Run Tests ---
            if test_file:
                test_run_output = run_pytest(test_file, temp_file, timeout=test_timeout)
                test_run_results['problems'][problem_number]['test_results'] = test_run_output
            else:
                logger.warning(f"No test case found for problem {problem_number} in Lab {lab_number}")
                test_run_results['problems'][problem_number]['test_results'] = {
                    'summary': {'status': 'no_test_file'},
                    'details': {'full_output': 'No corresponding test file found.'}
                }

            # --- Run Code Quality Checks ---
            quality_results = run_quality_checks(temp_file)

            # Store Flake8 results
            if 'flake8' in quality_results:
                flake8_run_results['problems'][problem_number]['flake8_results'] = quality_results['flake8']
            else:
                 flake8_run_results['problems'][problem_number]['flake8_results'] = {'error': 'Flake8 check failed or was not run.'}

            # Store Black results
            if 'black' in quality_results:
                black_run_results['problems'][problem_number]['black_results'] = quality_results['black']
            else:
                black_run_results['problems'][problem_number]['black_results'] = {'error': 'Black check failed or was not run.'}
            
        except Exception as e:
            error_message = f"Error processing file {file_path}: {str(e)}"
            logger.error(error_message, exc_info=True) # Log traceback
            # Record error in all result structures for this problem
            test_run_results['problems'][problem_number]['error'] = error_message
            flake8_run_results['problems'][problem_number]['error'] = error_message
            black_run_results['problems'][problem_number]['error'] = error_message
            continue # Skip to next file on error

        finally:
            # Clean up temporary file regardless of success or failure
            if temp_file and os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except Exception as e:
                    logger.warning(f"Could not remove temporary file {temp_file}: {str(e)}")

    # --- Save Results ---
    if test_run_results['problems']:
        save_json_results(
            test_run_results,
            test_results_dir,
            lab_number,
            student_name,
            student_id,
            result_type="test_results"
        )
        
    if flake8_run_results['problems']:
        save_json_results(
            flake8_run_results,
            flake8_results_dir,
            lab_number,
            student_name,
            student_id,
            result_type="flake8_results"
        )
        
    if black_run_results['problems']:
         save_json_results(
            black_run_results,
            black_results_dir,
            lab_number,
            student_name,
            student_id,
            result_type="black_results"
        )

def main():
    # Configuration
    submission_folder = 'submissions'  # Root folder containing all submissions
    rubric_dir = 'rubric'  # Directory containing test cases and where results will be stored
    base_results_dir = os.path.join(rubric_dir) # Base directory for all results

    # Create base results directory if it doesn't exist (redundant if subdirs are created later, but safe)
    os.makedirs(base_results_dir, exist_ok=True)
    
    # Get list of students
    students = get_student_list(submission_folder)
    
    # Process each student's submission
    for student in students:
        logger.info(f"Processing submission for {student['name']} ({student['id']}) in {student['lab_folder']}")
        # Pass the *base* results directory to run_tests_for_student
        run_tests_for_student(student, submission_folder, rubric_dir, base_results_dir) # Assuming default timeout

if __name__ == '__main__':
    main() 