import os
import pytest
import json
import re
from datetime import datetime
from assignment_marker.moodle_loader import get_student_list
from assignment_marker.student_code_extractor import extract_code_from_files
from code_testing.quality_runner_main import run_quality_checks
import io
from contextlib import redirect_stdout, redirect_stderr

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

def run_pytest(test_file, student_solution_path):
    """Run pytest on a specific test file and return results."""
    # Set the environment variable for the test to use
    os.environ['STUDENT_SOLUTION_PATH'] = student_solution_path
    
    # Capture both stdout and stderr
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    
    with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
        pytest_result = pytest.main(['-v', test_file])
    
    # Get the complete output and ensure proper line endings
    test_output = stdout_capture.getvalue().replace('\r\n', '\n').replace('\r', '\n')
    test_error = stderr_capture.getvalue().replace('\r\n', '\n').replace('\r', '\n')
    
    # Parse the test results to get more detailed information
    test_details = []
    for line in test_output.split('\n'):
        if 'test_' in line and '::' in line:
            test_details.append(line.strip())
    
    # Create a more detailed test summary
    test_summary = {
        'passed': pytest_result == pytest.ExitCode.OK,
        'exit_code': str(pytest_result),
        'test_output': test_output,
        'test_error': test_error if test_error else None,  # Only include if there are errors
        'test_details': test_details
    }
    
    return test_summary

def get_problem_number(file_name):
    """Extract problem number from various file naming formats."""
    # Try to find a number followed by optional letter after "Problem" or "Problem_" in the filename
    match = re.search(r'Problem[_\s]*(\d+[a-zA-Z]?)', file_name, re.IGNORECASE)
    if match:
        # Return the full match including any letter suffix
        return match.group(1)
    return None

def run_tests_for_student(student_info, submission_folder, rubric_dir, results_dir):
    """Run tests for a specific student and save results."""
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
        print(f"Could not find submission folder for student {student_name} ({student_id})")
        return
    
    # Initialize the combined results object
    combined_results = {
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
        print(f"No valid Python files found for student {student_name} ({student_id})")
        return
        
    # Extract code from student's files
    for file_path, problem_number in python_files:
        test_file = find_test_cases(rubric_dir, problem_number, lab_number)
        
        if test_file:
            try:
                # Extract code for this specific file
                student_code = extract_code_from_files([file_path])
                
                if not student_code:
                    print(f"Could not read file {file_path}")
                    continue
                
                # Create temporary file with student's code
                temp_dir = os.path.join(results_dir, 'temp')
                os.makedirs(temp_dir, exist_ok=True)
                temp_file = os.path.join(temp_dir, f'problem{problem_number}.py')
                
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(student_code[file_path])
                
                # Run tests with the student's solution path
                test_results = run_pytest(test_file, temp_file)
                
                # Run code quality checks
                quality_results = run_quality_checks(temp_file)
                
                # Calculate test statistics
                total_tests = len(test_results['test_details'])
                passed_tests = len([t for t in test_results['test_details'] if 'PASSED' in t])
                failed_tests = len([t for t in test_results['test_details'] if 'FAILED' in t])
                
                # Add this problem's results to the combined results
                problem_results = {
                    'solution_path': file_path,
                    'test_results': {
                        'summary': {
                            'passed': test_results['passed'],
                            'exit_code': test_results['exit_code'],
                            'total_tests': total_tests,
                            'passed_tests': passed_tests,
                            'failed_tests': failed_tests
                        },
                        'details': {
                            'test_cases': test_results['test_details'],
                            'full_output': test_results['test_output']
                        }
                    },
                    'code_quality': {
                        'summary': {
                            'has_quality_issues': any(
                                quality_results[tool]['has_issues'] 
                                for tool in quality_results
                            ) if quality_results else True,
                            'tools_run': list(quality_results.keys()) if quality_results else []
                        },
                        'tool_results': quality_results if quality_results else {}
                    }
                }
                
                # Add error output only if there are errors
                if test_results['test_error']:
                    problem_results['test_results']['details']['error_output'] = test_results['test_error']
                
                # Add to combined results
                combined_results['problems'][problem_number] = problem_results
                
                # Clean up temporary file
                try:
                    os.remove(temp_file)
                except Exception as e:
                    print(f"Warning: Could not remove temporary file {temp_file}: {str(e)}")
                
            except Exception as e:
                print(f"Error processing file {file_path}: {str(e)}")
                continue
    
    # Save combined results in lab-specific subdirectory
    if combined_results['problems']:
        # Create lab-specific results directory
        lab_results_dir = os.path.join(results_dir, f'Lab{lab_number}')
        os.makedirs(lab_results_dir, exist_ok=True)
        
        result_filename = f"{student_name}_{student_id}_Lab{lab_number}_results.json"
        result_path = os.path.join(lab_results_dir, result_filename)
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(combined_results, f, indent=4, ensure_ascii=False)

def main():
    # Configuration
    submission_folder = 'submissions'  # Root folder containing all submissions
    rubric_dir = 'rubric'  # Directory containing test cases
    results_dir = os.path.join(rubric_dir, 'test_results')
    
    # Create results directory if it doesn't exist
    os.makedirs(results_dir, exist_ok=True)
    
    # Get list of students
    students = get_student_list(submission_folder)
    
    # Process each student's submission
    for student in students:
        print(f"Processing submission for {student['name']} ({student['id']}) in {student['lab_folder']}")
        run_tests_for_student(student, submission_folder, rubric_dir, results_dir)

if __name__ == '__main__':
    main() 