import os
import pytest
import json
import re
import logging
import subprocess
import shutil
from datetime import datetime
from assignment_marker.student_code_extractor import extract_code_from_files
from code_testing.quality_runner_main import run_quality_checks
import io
from contextlib import redirect_stdout, redirect_stderr
import traceback
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import sys
import stat
import win32security
import ntsecuritycon as con

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

def find_test_cases(test_cases_dir: str, problem_number: str) -> Optional[str]:
    """Find test cases for a specific problem within the task's test case directory."""
    # Test file naming convention assumed: test_problem<number>.py
    test_file = Path(test_cases_dir) / f'test_problem{problem_number}.py'
    if test_file.exists():
        return str(test_file)
    logger.warning(f"Test case file not found: {test_file}")
    return None

def run_pytest(test_file: str, student_solution_path: str, timeout: int = 30) -> Dict[str, Any]:
    """Run pytest in a subprocess with a timeout and return structured results."""
    # Ensure STUDENT_SOLUTION_PATH is set for the subprocess environment
    env = os.environ.copy()
    env['STUDENT_SOLUTION_PATH'] = student_solution_path

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
        logger.debug(f"Running pytest command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env, # Pass modified environment
            check=False # Don't raise exception on non-zero exit code
        )

        stdout = result.stdout.replace('\r\n', '\n').replace('\r', '\n')
        stderr = result.stderr.replace('\r\n', '\n').replace('\r', '\n')
        exit_code = result.returncode

        logger.debug(f"Pytest finished. Exit Code: {exit_code}")
        # logger.debug(f"Pytest stdout:\n{stdout}") # Potentially very long
        if stderr:
             logger.debug(f"Pytest stderr:\n{stderr}")

        # Parse output for summary details
        passed = exit_code == pytest.ExitCode.OK
        summary['passed'] = passed
        summary['exit_code'] = str(exit_code) 
        summary['status'] = 'completed'

        parsed_test_cases_details = [] # For more structured failure info
        concise_full_output_parts = []

        # Extract short test summary info
        short_summary_match = re.search(r"={10,} short test summary info ={10,}(.*?)(?=={10,} end short test summary info ={10,}|={10,}|$)", stdout, re.DOTALL)
        if short_summary_match:
            concise_full_output_parts.append(short_summary_match.group(0).strip())
            # Extract overall counts from the last line of the short summary
            summary_line_from_short = short_summary_match.group(1).strip().split('\n')[-1]
            # Example: "========= 4 failed, 3 passed in 8.13s ========="
            passed_match = re.search(r'(\d+)\s+passed', summary_line_from_short)
            failed_match = re.search(r'(\d+)\s+failed', summary_line_from_short)
            error_match = re.search(r'(\d+)\s+error(?:ed)?', summary_line_from_short) # Match 'error' or 'errored'
            
            passed_tests = int(passed_match.group(1)) if passed_match else 0
            failed_tests_count = int(failed_match.group(1)) if failed_match else 0
            if error_match: failed_tests_count += int(error_match.group(1))

            summary['passed_tests'] = passed_tests
            summary['failed_tests'] = failed_tests_count
            summary['total_tests'] = passed_tests + failed_tests_count
        else:
            # Fallback if short summary not found (should be rare with pytest)
            logger.warning("Standard pytest short summary info not found.")
            # Basic counting from individual lines as a less reliable fallback
            test_lines = stdout.split('\n')
            passed_tests_fallback = 0
            failed_tests_fallback = 0
            for line in test_lines:
                if re.search(r'.*::test_\w+\s+PASSED', line): # More specific PASSED line
                    passed_tests_fallback +=1
                elif re.search(r'.*::test_\w+\s+(FAILED|ERROR)', line):
                    failed_tests_fallback +=1
            summary['passed_tests'] = passed_tests_fallback
            summary['failed_tests'] = failed_tests_fallback
            summary['total_tests'] = passed_tests_fallback + failed_tests_fallback

        # Extract detailed failures
        failures_section_match = re.search(r"={10,} FAILURES ={10,}(.*?)(?=={10,} short test summary info ={10,}|$)", stdout, re.DOTALL)
        if failures_section_match:
            failures_content = failures_section_match.group(1)
            # Split individual failures
            individual_failures = re.split(r"_{5,}\s+(test_\w+)\s+_{5,}", failures_content)
            
            concise_full_output_parts.append("\n========= DETAILED FAILURES =========")
            # The first part of split is usually empty or header before the first test name
            i = 1
            while i < len(individual_failures):
                test_name = individual_failures[i]
                failure_details_text = individual_failures[i+1] if (i+1) < len(individual_failures) else ""
                
                concise_failure_info = f"\n--- FAILURE: {test_name} ---"
                error_line_match = re.search(r"^E\s+.*AssertionError:(.*)", failure_details_text, re.MULTILINE)
                if not error_line_match:
                    error_line_match = re.search(r"^E\s+(.*?Error:.*)", failure_details_text, re.MULTILINE)
                
                error_message = error_line_match.group(1).strip() if error_line_match else "Unknown Error"
                concise_failure_info += f"\nError: {error_message}"
                
                # Extract a few lines of traceback context
                traceback_lines = failure_details_text.split('\n')
                context_lines = []
                capture_next_n = 0
                for line_idx, line in enumerate(traceback_lines):
                    if line.startswith('E   ') and error_message in line: # Start from error line
                        context_lines.append(line) 
                        # Capture a few lines after the error line, if they are part of the assertion explanation
                        for next_line_idx in range(line_idx + 1, min(line_idx + 4, len(traceback_lines))):
                            if traceback_lines[next_line_idx].strip().startswith(('+', 'where', '凶', 'E')) or not traceback_lines[next_line_idx].strip():
                                context_lines.append(traceback_lines[next_line_idx])
                            else:
                                break
                        break # Stop after capturing context for this error
                    elif line.strip().startswith('>') and 'in run_problem' not in line : # Lines indicating point of failure in test/student code
                         # Also capture a line or two before and after this indicator if they seem relevant
                        start_ctx = max(0, line_idx -1)
                        end_ctx = min(len(traceback_lines), line_idx + 2)
                        for ctx_idx in range(start_ctx, end_ctx):
                            if traceback_lines[ctx_idx] not in context_lines: # Avoid duplicates if already captured
                                context_lines.append(traceback_lines[ctx_idx])
                        # capture_next_n = 2 # capture this line and next N
                    # if capture_next_n > 0:
                    #     context_lines.append(line)
                    #     capture_next_n -=1
                
                if context_lines:
                    concise_failure_info += "\nRelevant Traceback Snippet:\n" + "\n".join(context_lines[-10:]) # Limit to last 10 for brevity
                
                concise_full_output_parts.append(concise_failure_info)
                parsed_test_cases_details.append({"name": test_name, "status": "FAILED", "error_message": error_message, "context": "\n".join(context_lines[-10:])})
                i += 2 # Move to the next test name
        
        # Collect PASSED test names from the initial collection part of stdout
        # Example: rubric/test_cases/.../test_problem1.py::test_read_files_function PASSED [ 14%]
        passed_test_names = re.findall(r"::(test_\w+)\s+PASSED", stdout)
        for pt_name in passed_test_names:
            # Avoid adding if already listed as failed (shouldn't happen with correct parsing)
            if not any(f_case['name'] == pt_name for f_case in parsed_test_cases_details):
                parsed_test_cases_details.append({"name": pt_name, "status": "PASSED"})

        details['test_cases'] = parsed_test_cases_details 
        details['full_output'] = "\n".join(concise_full_output_parts) 
        details['error_output'] = stderr if stderr else None

    except subprocess.TimeoutExpired as e:
        logger.warning(f"Pytest execution timed out for {test_file} after {timeout} seconds.")
        # summary and details are already set for timeout
        # Capture partial output if available
        if e.stdout: # e.stdout is already a string if text=True
            details['full_output'] += "\nPartial Output before Timeout:\n" + e.stdout.replace('\r\n', '\n').replace('\r', '\n')
        if e.stderr: # e.stderr is already a string if text=True
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

def get_problem_number(file_name: str) -> Optional[str]:
    """Extract problem number from various file naming formats."""
    # Remove extension
    base_name = Path(file_name).stem # Use pathlib for robustness

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

def save_json_results(data: Dict[str, Any], results_dir: str, student_name: str, student_id: str, task_name: str, result_type: str = "results") -> None:
    """Saves the provided data dictionary to a JSON file in the specified results directory."""
    # Results directory is now passed directly, ensure it exists
    results_path = Path(results_dir)
    results_path.mkdir(parents=True, exist_ok=True)
    
    # Updated filename format to match pipeline
    result_filename = f"{student_name.replace(' ', '_')}_{student_id}_{task_name}_submission.json"
    result_file_path = results_path / result_filename
    
    try:
        with open(result_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info(f"Successfully saved {result_type} to {result_file_path}")
    except Exception as e:
        logger.error(f"Failed to save {result_type} to {result_file_path}: {str(e)}")

def copy_data_files(test_cases_dir: str, submission_folder: str) -> List[str]:
    """Copy data files from test_cases directory to submission folder."""
    copied_files = []
    test_cases_path = Path(test_cases_dir)
    submission_path = Path(submission_folder)
    
    # Find all non-python, non-test files
    for file in test_cases_path.glob('*'):
        # Skip __pycache__ directories and hidden files
        if file.name.startswith('.') or file.name == '__pycache__':
            continue
            
        if file.is_file():
            # Skip test files and Python files
            if file.name.startswith('test_') or file.suffix == '.py':
                continue
                
            try:
                dest_path = submission_path / file.name
                shutil.copy2(file, dest_path)
                # Set read permissions for copied files
                set_windows_permissions(str(dest_path), read_only=True)
                copied_files.append(str(dest_path))
                logger.info(f"Copied data file: {file.name} to submission folder")
            except Exception as e:
                logger.error(f"Failed to copy data file {file.name}: {str(e)}")
    
    return copied_files

def cleanup_data_files(file_paths: List[str]) -> None:
    """Remove temporary data files from submission folder."""
    for file_path in file_paths:
        try:
            os.remove(file_path)
            logger.info(f"Removed temporary data file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to remove temporary file {file_path}: {str(e)}")

def install_required_packages(submission_folder: str, student_code: str) -> None:
    """Install required packages from student code."""
    # List of built-in Python modules that don't need installation
    built_in_modules = {
        'os', 'sys', 'math', 'datetime', 'json', 're', 'random', 'collections',
        'itertools', 'functools', 'pathlib', 'shutil', 'subprocess', 'tempfile',
        'time', 'copy', 'string', 'statistics', 'decimal', 'fractions'
    }
    
    # Extract import statements
    import_pattern = r'^(?:from|import)\s+([a-zA-Z0-9_\.]+)'
    imports = set()
    
    for line in student_code.split('\n'):
        match = re.match(import_pattern, line.strip())
        if match:
            package = match.group(1).split('.')[0]
            if package not in built_in_modules: imports.add(package)
    
    if not imports: 
        logger.info("No external packages identified for installation check.")
        return

    logger.info(f"Identified potential external packages: {list(imports)}")
    
    pip_install_candidates = set(imports) # Start with all identified imports
    submission_dir_path = Path(submission_folder) # submission_folder is the temp_dir

    for imp_name in list(imports): # Iterate over original set of imports
        # Check 1: Is it a .py file in the root of the temp_dir?
        if (submission_dir_path / f"{imp_name}.py").exists():
            logger.info(f"Identified '{imp_name}' as a local module file. Will not attempt to pip install.")
            if imp_name in pip_install_candidates: pip_install_candidates.remove(imp_name)
            continue
        
        # Check 2: Is it a directory in the root of the temp_dir (could be a package or namespace package)?
        # This also implicitly covers cases with __init__.py for formal packages.
        potential_package_path = submission_dir_path / imp_name
        if potential_package_path.is_dir():
            logger.info(f"Identified '{imp_name}' as a local directory/package. Will not attempt to pip install.")
            if imp_name in pip_install_candidates: pip_install_candidates.remove(imp_name)
            continue
        
        # Check 3: Heuristic for multi-level imports like `helpers.utils` where `helpers` is a dir.
        # If `imp_name` is the first part of a multi-level import (e.g. `helpers` from `helpers.utils`),
        # and `helpers` is a directory, we assume it's a local package structure.
        # Note: The import_pattern already extracts the base package name, so this check is implicitly covered by Check 2.
        # However, if the import was `import my_module.my_sub_module` and `my_module.py` exists, check 1 handles it.
        # If `import my_package.my_module` and `my_package/` is a dir, check 2 handles `my_package`.

    if not pip_install_candidates:
        logger.info("All identified imports are either built-in or appear to be local modules/packages. No pip install needed.")
        return

    logger.info(f"Checking pip for remaining required packages: {list(pip_install_candidates)}")
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'list', '--format=json'], check=True, capture_output=True, text=True)
        installed_packages = {pkg['name'].lower() for pkg in json.loads(result.stdout)}
        packages_to_install = [pkg for pkg in pip_install_candidates if pkg.lower() not in installed_packages]
            
        if packages_to_install:
            logger.info(f"Installing missing packages: {', '.join(packages_to_install)}")
            subprocess.run(
                [sys.executable, '-m', 'pip', 'install'] + packages_to_install,
                check=True,
                capture_output=True,
                text=True
            )
        else:
            logger.info("All required packages are already installed")
            
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install packages: {e.stderr}")
    except json.JSONDecodeError:
        logger.error("Failed to parse pip list output")

def set_windows_permissions(file_path: str, read_only: bool = True) -> None:
    """Set Windows file permissions."""
    try:
        # Get the security descriptor
        sd = win32security.GetFileSecurity(
            file_path, 
            win32security.DACL_SECURITY_INFORMATION
        )
        
        # Get the DACL
        dacl = sd.GetSecurityDescriptorDacl()
        
        # Get the current user's SID
        username = os.environ.get('USERNAME', 'Everyone')
        sid = win32security.LookupAccountName(None, username)[0]
        
        # Set permissions
        if read_only:
            # Read-only permissions
            dacl.AddAccessAllowedAce(
                win32security.ACL_REVISION,
                con.FILE_GENERIC_READ,
                sid
            )
        else:
            # Full control permissions
            dacl.AddAccessAllowedAce(
                win32security.ACL_REVISION,
                con.FILE_ALL_ACCESS,
                sid
            )
        
        # Apply the new DACL
        sd.SetSecurityDescriptorDacl(1, dacl, 0)
        win32security.SetFileSecurity(
            file_path,
            win32security.DACL_SECURITY_INFORMATION,
            sd
        )
    except Exception as e:
        logger.warning(f"Failed to set Windows permissions for {file_path}: {str(e)}")

def convert_notebook_to_script(notebook_path: str) -> str:
    """Convert a Jupyter notebook to a Python script and return the path to the script."""
    try:
        # Create a temporary Python script path
        script_path = str(Path(notebook_path).with_suffix('.py'))
        
        # Convert notebook to Python script
        cmd = [
            sys.executable, 
            '-m', 
            'jupyter', 
            'nbconvert', 
            '--to', 
            'script', 
            notebook_path, 
            '--output', 
            str(Path(script_path).stem)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True
        )
        
        if not Path(script_path).exists():
            raise FileNotFoundError(f"Failed to create Python script from notebook: {notebook_path}")
        
        # Set read permissions for the converted script
        set_windows_permissions(script_path, read_only=True)
        
        # Also set permissions for the parent directory
        set_windows_permissions(str(Path(script_path).parent), read_only=False)
            
        return script_path
        
    except Exception as e:
        logger.error(f"Error converting notebook to script: {str(e)}")
        raise

def run_tests_for_student(
    student_info: Dict[str, str],
    submission_folder: str,
    test_cases_dir: str,
    results_dir: str,
    task_name: str,
    test_timeout: int = 30,
    install_packages: bool = True
) -> None:
    """Run tests and quality checks for a student's submission for a specific task."""
    student_id = student_info['id']
    student_name = student_info['name']
    
    logger.info(f"Starting test run for student {student_name} ({student_id}) on task {task_name}")
    submission_path = Path(submission_folder) # Original submission folder path

    # Create a temporary directory for running tests
    temp_dir = Path(results_dir).parent / 'temp' / task_name / f"{student_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    set_windows_permissions(str(temp_dir), read_only=False)
    
    # --- Prepare file lists and copy to temp_dir ---
    # Stores (path_in_temp_dir, problem_number, file_type, original_absolute_path)
    files_to_process_info: List[Tuple[str, str, str, str]] = []
    # Keep track of all files copied to temp_dir to ensure they are available for local imports
    all_copied_temp_files = [] 

    for item_in_submission in submission_path.rglob('*'):
        if item_in_submission.is_file() and not (item_in_submission.name.startswith('.') or '__pycache__' in str(item_in_submission)):
            relative_path = item_in_submission.relative_to(submission_path)
            current_path_in_temp_dir = temp_dir / relative_path
            current_path_in_temp_dir.parent.mkdir(parents=True, exist_ok=True)

            problem_number = get_problem_number(item_in_submission.name)
            
            if problem_number:
                # This is a main solution file to be tested
                file_type = 'ipynb' if item_in_submission.suffix == '.ipynb' else 'py'
                original_absolute_path = str(item_in_submission.resolve())
                try:
                    shutil.copy2(item_in_submission, current_path_in_temp_dir)
                    set_windows_permissions(str(current_path_in_temp_dir), read_only=True)
                    set_windows_permissions(str(current_path_in_temp_dir.parent), read_only=False)
                    files_to_process_info.append((
                        str(current_path_in_temp_dir.resolve()), 
                        problem_number, 
                        file_type, 
                        original_absolute_path
                    ))
                    all_copied_temp_files.append(str(current_path_in_temp_dir.resolve()))
                except Exception as e:
                    logger.error(f"Failed to copy main solution file {item_in_submission.name} to temp_dir: {e}")
            elif item_in_submission.suffix.lower() in ['.py', '.csv', '.txt', '.json']: 
                # This is an auxiliary file (helper script, data file submitted by student)
                # Copy it to maintain the relative structure for imports.
                try:
                    shutil.copy2(item_in_submission, current_path_in_temp_dir)
                    set_windows_permissions(str(current_path_in_temp_dir), read_only=True) # Usually read-only is fine
                    set_windows_permissions(str(current_path_in_temp_dir.parent), read_only=False)
                    all_copied_temp_files.append(str(current_path_in_temp_dir.resolve()))
                    logger.info(f"Copied auxiliary file {item_in_submission.name} to {current_path_in_temp_dir}")
                except Exception as e:
                    logger.error(f"Failed to copy auxiliary file {item_in_submission.name} to temp_dir: {e}")
            else:
                logger.info(f"Skipping file {item_in_submission.name} (not a primary solution file or recognized auxiliary type).")
    
    if not files_to_process_info:
        logger.warning(f"No processable Python or notebook files with determinable problem numbers found for student {student_name} ({student_id}) in {submission_folder}")
        # Ensure JSON files are still created if downstream processes expect them
        # (Code to save empty/error JSONs can be added here if necessary)
        return

    logger.info(f"Found {len(files_to_process_info)} code file(s) to process for student {student_name}.")

    # Copy data files to temp directory (after temp_dir is confirmed and files are copied)
    copied_data_files = copy_data_files(test_cases_dir, str(temp_dir))
    converted_scripts = []

    try:
        base_dir = Path(results_dir).parent.parent
        sub_dirs = {
            'test_results': base_dir / 'test_results' / task_name,
            'flake8_result': base_dir / 'flake8_result' / task_name,
            'black_result': base_dir / 'black_result' / task_name
        }
        for dir_path in sub_dirs.values():
                dir_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().isoformat()
        student_info_dict = {'name': student_name, 'id': student_id}
        
        test_results_json = {'metadata': {'student_name': student_name, 'student_id': student_id, 'task_name': task_name, 'timestamp': timestamp, 'student_info': student_info_dict}, 'problems': {}}
        flake8_results_json = {'metadata': {'student_name': student_name, 'student_id': student_id, 'task_name': task_name, 'timestamp': timestamp, 'student_info': student_info_dict}, 'problems': {}}
        black_results_json = {'metadata': {'student_name': student_name, 'student_id': student_id, 'task_name': task_name, 'timestamp': timestamp, 'student_info': student_info_dict}, 'problems': {}}

        for path_in_temp_str, problem_number, file_type_in_temp, original_absolute_path_for_json in files_to_process_info:
            logger.info(f"Processing file from temp_dir: {path_in_temp_str} for problem: {problem_number} (type: {file_type_in_temp})")
            
            test_file_for_problem = find_test_cases(test_cases_dir, problem_number)

            test_results_json['problems'][problem_number] = {'solution_path': original_absolute_path_for_json, 'test_results': None, 'error': None}
            flake8_results_json['problems'][problem_number] = {'solution_path': original_absolute_path_for_json, 'flake8_results': None, 'error': None}
            black_results_json['problems'][problem_number] = {'solution_path': original_absolute_path_for_json, 'black_results': None, 'error': None}

            path_for_processing_str = path_in_temp_str # This is the path inside temp_dir to the .py or .ipynb

            try:
                if file_type_in_temp == 'ipynb':
                    try:
                        # Convert notebook (which is in temp_dir) to a script (also in temp_dir)
                        converted_script_path_str = convert_notebook_to_script(path_in_temp_str)
                        converted_scripts.append(converted_script_path_str)
                        path_for_processing_str = converted_script_path_str # Now points to the .py script
                        logger.info(f"Converted notebook {path_in_temp_str} to script: {path_for_processing_str}")
                        set_windows_permissions(path_for_processing_str, read_only=True)
                        set_windows_permissions(str(Path(path_for_processing_str).parent), read_only=False)
                    except Exception as e:
                        raise ValueError(f"Failed to convert notebook {path_in_temp_str} to script: {str(e)}")

                code_dict = extract_code_from_files([path_for_processing_str])
                if not code_dict or path_for_processing_str not in code_dict:
                    raise ValueError(f"Could not read/extract code from file: {path_for_processing_str}")
                student_code_content = code_dict[path_for_processing_str]

                if install_packages:
                    install_required_packages(str(temp_dir), student_code_content)

                if test_file_for_problem:
                    logger.info(f"Running tests using: {test_file_for_problem} for student solution: {path_for_processing_str}")
                    # Pass the path_for_processing_str (actual .py script in temp_dir) as the student_solution_path for pytest's environment
                    pytest_output = run_pytest(test_file_for_problem, path_for_processing_str, timeout=test_timeout)
                    test_results_json['problems'][problem_number]['test_results'] = pytest_output
                else:
                    logger.warning(f"No test case found for problem {problem_number} in {test_cases_dir}")
                    test_results_json['problems'][problem_number]['test_results'] = {
                        'summary': {'status': 'no_test_file', 'passed': False, 'exit_code': 'N/A', 'total_tests': 0, 'passed_tests': 0, 'failed_tests': 0},
                        'details': {'test_cases': [], 'full_output': f'No corresponding test file found in {test_cases_dir}.'}
                    }

                logger.info(f"Running quality checks on: {path_for_processing_str}")
                quality_run_results = run_quality_checks(path_for_processing_str)

                if 'flake8' in quality_run_results:
                    flake8_results_json['problems'][problem_number]['flake8_results'] = quality_run_results['flake8']
                else:
                    flake8_results_json['problems'][problem_number]['flake8_results'] = {'error': 'Flake8 check failed or was not run.', 'has_issues': False}

                if 'black' in quality_run_results:
                    black_results_json['problems'][problem_number]['black_results'] = quality_run_results['black']
                else:
                    black_results_json['problems'][problem_number]['black_results'] = {'error': 'Black check failed or was not run.', 'has_issues': False}

            except Exception as e:
                error_msg = f"Error processing file {path_in_temp_str} for problem {problem_number}: {str(e)}"
                logger.error(error_msg, exc_info=True)
                test_results_json['problems'][problem_number]['error'] = error_msg
                flake8_results_json['problems'][problem_number]['error'] = error_msg
                black_results_json['problems'][problem_number]['error'] = error_msg
                if test_results_json['problems'][problem_number]['test_results'] is None:
                    test_results_json['problems'][problem_number]['test_results'] = {'summary': {'status': 'error', 'passed': False}, 'details': {'full_output': error_msg}}

        # Save all results
        if test_results_json['problems']:
            save_json_results(test_results_json, str(sub_dirs['test_results']), student_name, student_id, task_name, "test_results")
        if flake8_results_json['problems']:
            save_json_results(flake8_results_json, str(sub_dirs['flake8_result']), student_name, student_id, task_name, "flake8_results")
        if black_results_json['problems']:
            save_json_results(black_results_json, str(sub_dirs['black_result']), student_name, student_id, task_name, "black_results")

    except Exception as e_outer: # General exception handler for the outer try block (T1)
        logger.critical(f"A critical error occurred during run_tests_for_student for {student_name} ({student_id}), task {task_name}: {e_outer}", exc_info=True)
        # Optionally, save a minimal error JSON or take other recovery actions
        # For now, this will proceed to the finally block for cleanup.

    finally: # Corresponds to Outer try (T1)
        try:
            cleanup_data_files(copied_data_files)
            for script_path_to_remove in converted_scripts:
                try:
                    if Path(script_path_to_remove).exists():
                        os.remove(script_path_to_remove)
                        logger.info(f"Removed temporary converted script: {script_path_to_remove}")
                except Exception as e_rem_script:
                    logger.warning(f"Failed to remove temporary script {script_path_to_remove}: {str(e_rem_script)}")
            
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
        except Exception as e_cleanup:
            logger.error(f"Failed to clean up temporary directory {temp_dir}: {e_cleanup}")

# Removed main() function as this module is not intended to be run standalone anymore
# if __name__ == '__main__':
#     main() 