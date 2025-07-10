import os
import argparse
import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging
from code_testing.test_runner_main import run_tests_for_student
# from llm_feedback.feedback_generator import generate_feedback, FeedbackFormat # Old monolithic feedback
# from llm_feedback.report_generator import generate_report # Old monolithic report
from llm_feedback.module_feedback_generator import generate_feedback_for_module # New modular generator
from assignment_marker.moodle_loader import get_user_list_for_task
from assignment_marker.folder_structure_parser import read_submission_files
from assignment_marker.student_code_extractor import (
    extract_code_from_files, 
    extract_markdown_from_ipynb, 
    extract_text_from_document
)
from assignment_marker.rubric_repository import RubricRepository

# Configure logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),  # Log to stdout
        logging.FileHandler('modules_pipeline.log')  # Log to a new file
    ]
)
logger = logging.getLogger(__name__) # Will be 'modules_pipeline'

class SmartFormatter(argparse.HelpFormatter):
    """Formatter that handles special characters in usage examples."""
    def _split_lines(self, text, width):
        if text.startswith('R|'):
            return text[2:].splitlines()
        return argparse.HelpFormatter._split_lines(self, text, width)

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Run the MODULAR marking pipeline for student submissions based on tasks and defined modules.',
        formatter_class=SmartFormatter
    )
    
    parser.add_argument(
        '--task-name',
        type=str,
        required=True,
        help="""R|Name of the task to process (e.g., Lab1, Ass2).
This corresponds to a key in the config file and a folder in the submissions directory."""
    )
    
    parser.add_argument(
        '--submissions-dir',
        type=str,
        default='submissions',
        help="""R|Path to the base submissions directory.
Expected structure: submissions_dir / task_name / user_submission_folder
For paths with spaces or special characters, use quotes:
--submissions-dir "path/to/submissions folder" """  # Ensure exactly three closing quotes
    )
    
    parser.add_argument(
        '--config-file',
        type=str,
        default='rubric/marking_config.yaml', # Default assumes config is in rubric dir
        help='Path to the main YAML configuration file defining tasks, modules, and their settings.'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default='openai-gpt-o1-mini',
        help='Name of the LLM model to use for feedback generation (default: openai-gpt-o1-mini)'
    )
    
    parser.add_argument(
        '--feedback-format',
        type=str,
        choices=['html', 'markdown', 'text'],
        default='markdown',
        help='Format of the generated feedback (default: markdown)'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help='Set the logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        default='modules_pipeline.log', # Default log file name changed
        help='Path to log file (default: modules_pipeline.log)'
    )
    
    parser.add_argument(
        '--skip-feedback',
        action='store_true',
        help='Skip feedback generation and only run tests'
    )
    
    parser.add_argument(
        '--skip-tests',
        action='store_true',
        help='Skip test running and only generate feedback'
    )
    
    parser.add_argument(
        '--test-timeout',
        type=int,
        default=30,  # Default timeout of 30 seconds
        help='Maximum time in seconds allowed for running tests for a single problem/task (default: 30)'
    )

    parser.add_argument(
        '--exclude',
        nargs='+',
        choices=['black', 'flake8'],
        default=[],
        help='Exclude specific code quality tools from LLM feedback (choices: black, flake8)'
    )
    
    parser.add_argument(
        '--install-packages',
        action='store_true',
        default=True,
        help='Install required packages from student code (default: True)'
    )
    
    parser.add_argument(
        '--output-target',
        type=str,
        choices=['student_feedback', 'marker_report'],
        default='student_feedback',
        help='Specify whether to generate feedback for students or a report for markers (default: student_feedback)'
    )

    parser.add_argument(
        '--temperature',
        type=float,
        default=0.1, # Default temperature for LLM
        help='Temperature for LLM generation (e.g., 0.2 for more deterministic, 0.7 for more creative). Default: 0.2'
    )
    
    args = parser.parse_args()
    
    # Handle path normalization
    args.submissions_dir = str(Path(args.submissions_dir).resolve())
    args.log_file = str(Path(args.log_file).resolve())
    args.config_file = str(Path(args.config_file).resolve()) # Normalize config file path
    
    return args

def setup_logging(log_level: str, log_file: str) -> None:
    """Setup logging configuration."""
    # Remove existing handlers
    logger.handlers = []
    
    # Create formatters
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create file handler
    # Ensure the directory for the log file exists
    log_file_path = Path(log_file)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Setup console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Set log level
    logger.setLevel(getattr(logging, log_level))

def setup_directories(task_name: str) -> Dict[str, Path]:
    """Setup required directories for the marking pipeline based on the task."""
    base_dir = Path.cwd()
    
    # Define directory structure relative to the task
    # Assume config file is in 'rubric' parent dir, adjust if needed
    config_base_dir = base_dir / 'rubric' 
    
    dirs = {
        # Keep submissions separate, actual user folders are inside task subfolder
        'submissions_base': base_dir / 'submissions', 
        'config_base': config_base_dir,
        # Task-specific directories
        'test_cases': config_base_dir / 'test_cases' / task_name,
        'test_results': config_base_dir / 'test_results' / task_name,
        'feedback': base_dir / 'feedback' / task_name
    }
    
    # Create task-specific directories if they don't exist
    for key, dir_path in dirs.items():
        if key not in ['submissions_base', 'config_base']: # Don't create base dirs here
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logger.error(f"Failed to create directory {dir_path}: {e}")
                # Decide if this is a critical failure or can be handled later
    
    return dirs

def validate_inputs(args: argparse.Namespace) -> Optional[str]:
    """Validate input parameters."""
    # Validate task name (basic check, could add regex)
    if not args.task_name or not args.task_name.strip():
        return "Task name cannot be empty."
    
    # Validate base submissions directory existence
    if not Path(args.submissions_dir).is_dir():
        return f"Base submissions directory not found: {args.submissions_dir}"
        
    # Validate task-specific submissions directory existence (optional check, depends on workflow)
    task_submission_path = Path(args.submissions_dir) / args.task_name
    if not task_submission_path.is_dir():
        logger.warning(f"Task-specific submission directory not found: {task_submission_path}. Proceeding, but no users might be found.")
        # Depending on strictness, could return an error here:
        # return f"Task-specific submission directory not found: {task_submission_path}"
        
    # Validate config file existence
    if not Path(args.config_file).is_file():
        return f"Configuration file not found: {args.config_file}"
    
    # Validate log file directory writability (already handled in setup_logging, but can double-check)
    try:
        log_file_path = Path(args.log_file)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        # Try opening the log file in append mode to check permissions
        with open(log_file_path, 'a'): 
            pass 
    except Exception as e:
        return f"Failed to access or create log file directory for {args.log_file}: {str(e)}"
    
    return None

def process_task(args: argparse.Namespace) -> None:
    """Process all submissions for a specific task."""
    task_name = args.task_name
    
    # Setup directories based on task name
    dirs = setup_directories(task_name)
    
    # Initialize repository with the main config file
    config_repo = RubricRepository(args.config_file)
    
    # Get the specific configuration for this task
    task_config = config_repo.get_task_config(task_name)
    if not task_config:
        logger.error(f"Configuration for task '{task_name}' not found in {args.config_file}")
        return
    logger.info(f"Loaded configuration for task: {task_name}")
    # Example: Access config details like task_config.get('description', 'No description')

    # Get list of users who submitted for this task
    # Pass the base submissions directory and the task name
    users = get_user_list_for_task(args.submissions_dir, task_name)
    if not users:
        logger.warning(f"No user submissions found for task '{task_name}' in {Path(args.submissions_dir) / task_name}")
        return # Nothing to process for this task
    
    logger.info(f"Found {len(users)} user submissions for task '{task_name}'")
    
    # Process each user's submission for the task
    for user_info in users:
        user_id = user_info['id']
        user_name = user_info['name']
        user_submission_folder = user_info.get('submission_folder_path') # Get the full path added earlier

        if not user_submission_folder or not Path(user_submission_folder).is_dir():
            logger.error(f"Submission folder path missing or invalid for user {user_name} ({user_id}). Skipping.")
            continue

        logger.info(f"Processing user: {user_name} ({user_id}) for task: {task_name}")
        
        try:
            # Submission files are within the user's specific folder
            submission_files_paths = read_submission_files(user_submission_folder)
            if not submission_files_paths:
                logger.warning(f"No processable files (.py, .ipynb) found in submission folder for user {user_name}. Skipping.")
                continue
            
            # Extract code, markdown, and text from all relevant files
            student_code_dict: Dict[str, str] = {}
            # Store markdown content per ipynb file
            student_markdown_dict: Dict[str, str] = {}
            all_document_text: Dict[str, str] = {}

            code_file_paths_for_extraction = [] # For extract_code_from_files
            for file_path_str in submission_files_paths:
                file_path_obj = Path(file_path_str)
                if file_path_str.endswith('.ipynb'):
                    code_file_paths_for_extraction.append(file_path_str)
                    # Extract and store markdown per notebook
                    markdown_list = extract_markdown_from_ipynb(file_path_str)
                    student_markdown_dict[file_path_obj.name] = "\n\n---\n\n".join(markdown_list) # Concatenate with a separator
                elif file_path_str.endswith('.py'):
                    code_file_paths_for_extraction.append(file_path_str)
                elif file_path_str.endswith(('.pdf', '.docx', '.doc', '.txt')):
                    text = extract_text_from_document(file_path_str)
                    if text:
                        all_document_text[Path(file_path_str).name] = text
            
            if code_file_paths_for_extraction:
                student_code_dict = extract_code_from_files(code_file_paths_for_extraction)
            
            if not student_code_dict and not student_markdown_dict and not all_document_text:
                logger.error(f"Could not extract any content (code, markdown, or text) for {user_name}. Files: {submission_files_paths}")
                continue
                
            # --- Test Running ---
            test_results_data = None
            if not args.skip_tests:
                logger.info(f"Running tests for {user_name} ({user_id}) on task {task_name}")
                
                # Construct paths for test runner
                # Assuming run_tests_for_student needs user info, the user's specific submission *folder*,
                # the base directory for test cases, and the base directory for results.
                # **Crucially, update run_tests_for_student signature and logic if necessary**
                try:
                    test_results_data = run_tests_for_student(
                        student_info={'id': user_id, 'name': user_name}, # Pass necessary user identifiers
                        submission_folder=user_submission_folder,        # Path to the specific user's files for this task
                        test_cases_dir=str(dirs['test_cases']),          # Task-specific test cases
                        results_dir=str(dirs['test_results']),           # Task-specific results directory
                        task_name=task_name,                             # Pass task name for context/naming
                        test_timeout=args.test_timeout,                  # Pass timeout
                        install_packages=args.install_packages           # Pass install_packages flag
                    )
                    logger.info(f"Tests completed for {user_name} ({user_id})")
                except Exception as test_err:
                    logger.error(f"Error running tests for {user_name} ({user_id}): {test_err}")
                    logger.exception("Detailed test runner error traceback:")
                    # Continue to feedback if possible, or skip user
                    continue 
            else:
                logger.info(f"Skipping tests for {user_name} ({user_id}) as requested.")

            # Define paths for results and quality files, accessible by both feedback and report generation
            results_filename = f"{user_name.replace(' ', '_')}_{user_id}_{task_name}_submission.json"
            results_file_path = dirs['test_results'] / results_filename
            quality_flake8_path = dirs['test_results'].parent / 'flake8_result' / task_name / results_filename.replace('_submission.json', '_flake8_results.json')
            quality_black_path = dirs['test_results'].parent / 'black_result' / task_name / results_filename.replace('_submission.json', '_black_results.json')

            # --- Modular Feedback Processing --- 
            # This section will replace the monolithic feedback/report generation

            if not task_config.get('modules'):
                logger.error(f"No modules defined for task '{task_name}' in config. Skipping LLM processing for {user_name}.")
                continue

            # Prepare results data for easy lookup if it exists
            # This assumes test_results_data is a dictionary where keys might match
            # parts of required_data in module configurations.
            # For example, test_results_data = {"q1_tests": ..., "q2_tests": ...}
            # Or, if test_results_data is a list of results, it might need preprocessing here.
            # For now, assume it's a dict or None.
            parsed_test_results = test_results_data if isinstance(test_results_data, dict) else {}

            # Load Flake8 and Black results if they exist, making them accessible.
            # This is a simplified loading; actual parsing of these JSONs might be needed.
            flake8_data = None
            if quality_flake8_path.exists():
                try:
                    with open(quality_flake8_path, 'r') as f:
                        flake8_data = f.read() # Or json.load(f)
                    logger.debug(f"Loaded Flake8 data from {quality_flake8_path}")
                except Exception as e:
                    logger.warning(f"Could not load Flake8 data from {quality_flake8_path}: {e}")
            
            black_data = None
            if quality_black_path.exists():
                try:
                    with open(quality_black_path, 'r') as f:
                        black_data = f.read() # Or json.load(f)
                    logger.debug(f"Loaded Black data from {quality_black_path}")
                except Exception as e:
                    logger.warning(f"Could not load Black data from {quality_black_path}: {e}")

            all_module_outputs = {} # Store outputs from each module, keyed by module_id

            for module_config in task_config.get('modules', []):
                module_id = module_config.get('module_id')
                if not module_id:
                    logger.warning(f"Module in task '{task_name}' is missing an ID. Skipping.")
                    continue
                
                logger.info(f"Processing module: {module_id} for user {user_name}")

                # 1. Gather data for this specific module based on module_config.required_data
                prompt_template_vars = {}
                
                # required_data is now expected to be a dictionary:
                # { "placeholder_in_prompt": "data_type:specifier", ... }
                # e.g., { "q1_code": "code_file:actual_filename.py", "q1_tests": "test_group:q1" }
                for placeholder_name, data_source_specifier in module_config.get('required_data', {}).items():
                    data_parts = data_source_specifier.split(':', 1)
                    data_type = data_parts[0]
                    data_specifier = data_parts[1] if len(data_parts) > 1 else None

                    # Use placeholder_name directly as the key for prompt_template_vars
                    if data_type == 'code_file' and data_specifier:
                        # data_specifier is the filename key expected in student_code_dict
                        if student_code_dict.get(data_specifier):
                            prompt_template_vars[placeholder_name] = student_code_dict[data_specifier]
                        else:
                            logger.warning(f"Module {module_id}: Code file '{data_specifier}' (for placeholder '{placeholder_name}') not found in student submission for {user_name}.")
                            prompt_template_vars[placeholder_name] = "" # Provide empty string
                    
                    elif data_type == 'all_code': # Special case for all code concatenated
                        prompt_template_vars[placeholder_name] = "\n".join(student_code_dict.values())

                    elif data_type == 'test_group' and data_specifier:
                        # data_specifier is the key expected in parsed_test_results
                        if parsed_test_results.get(data_specifier):
                            prompt_template_vars[placeholder_name] = parsed_test_results[data_specifier]
                        else:
                            logger.warning(f"Module {module_id}: Test results for group '{data_specifier}' (for placeholder '{placeholder_name}') not found for {user_name}.")
                            prompt_template_vars[placeholder_name] = {} # Provide empty dict

                    elif data_type == 'document_file' and data_specifier:
                        # data_specifier is the filename key expected in all_document_text
                        if all_document_text.get(data_specifier):
                            prompt_template_vars[placeholder_name] = all_document_text[data_specifier]
                        else:
                            logger.warning(f"Module {module_id}: Document file '{data_specifier}' (for placeholder '{placeholder_name}') not found for {user_name}.")
                            prompt_template_vars[placeholder_name] = ""

                    elif data_type == 'markdown_file' and data_specifier:
                        # data_specifier is the .ipynb filename key expected in student_markdown_dict
                        if student_markdown_dict.get(data_specifier):
                            prompt_template_vars[placeholder_name] = student_markdown_dict[data_specifier]
                        else:
                            logger.warning(f"Module {module_id}: Markdown content for file '{data_specifier}' (for placeholder '{placeholder_name}') not found for {user_name}.")
                            prompt_template_vars[placeholder_name] = ""                            
                            
                    elif data_type == 'all_markdown_content': # This provides all markdown from ALL ipynb files combined
                        all_md_combined = []
                        for md_content in student_markdown_dict.values():
                            all_md_combined.append(md_content)
                        prompt_template_vars[placeholder_name] = "\n\n---\n\n".join(all_md_combined)
                    
                    elif data_type == 'flake8_report_data': # Changed for clarity
                        prompt_template_vars[placeholder_name] = flake8_data if flake8_data else "No Flake8 output available."
                    
                    elif data_type == 'black_report_data': # Changed for clarity
                        prompt_template_vars[placeholder_name] = black_data if black_data else "No Black output available."
                    
                    else:
                        logger.warning(f"Module {module_id}: Unknown data_source_specifier '{data_source_specifier}' for placeholder '{placeholder_name}' for {user_name}.")
                        prompt_template_vars[placeholder_name] = f"[Data not found for {placeholder_name}]"

                # Add other general context if needed by prompts (e.g. task_name, user_name)
                prompt_template_vars['task_name'] = task_name
                prompt_template_vars['user_name'] = user_name
                # Add more global vars as needed, e.g. full student_code_dict if a module needs it all
                prompt_template_vars['all_student_code'] = student_code_dict
                # Replace all_markdown_content with the new dict for more specific access if needed by some templates
                prompt_template_vars['all_student_markdown_by_file'] = student_markdown_dict 
                prompt_template_vars['all_document_text'] = all_document_text
                prompt_template_vars['all_test_results'] = parsed_test_results

                # 2. Get module-specific prompt and populate it
                system_prompt_template = module_config.get('system_prompt_template', "You are a helpful teaching assistant providing feedback on a specific part of a student\'s assignment.") # Default system prompt
                user_prompt_template = module_config.get('user_prompt_template', "")
                output_model_name = module_config.get('output_model_name', 'TextFeedback') # Get from config, default to TextFeedback

                if not user_prompt_template:
                    logger.warning(f"Module {module_id} has no user_prompt_template. Skipping LLM call.")
                    all_module_outputs[module_id] = "Error: User prompt template missing for this module."
                    continue
                
                populated_system_prompt = ""
                populated_user_prompt = ""

                try:
                    populated_system_prompt = system_prompt_template.format(**prompt_template_vars)
                    populated_user_prompt = user_prompt_template.format(**prompt_template_vars)
                except KeyError as e:
                    # Corrected KeyError logging
                    logger.error(f"Module {module_id}: Missing key '{e!s}' in prompt_template_vars when populating prompts for {user_name}. System: '{system_prompt_template}', User: '{user_prompt_template}'")
                    all_module_outputs[module_id] = f"Error: Configuration error for prompt variables (missing key: {e!s})."
                    continue
                except Exception as e:
                    logger.error(f"Module {module_id}: Error populating prompts for {user_name}: {e}. System: '{system_prompt_template}', User: '{user_prompt_template}'")
                    all_module_outputs[module_id] = "Error: Could not populate prompts for this module."
                    continue

                # 3. Call LLM for this module
                if not args.skip_feedback: # Re-using skip_feedback flag
                    module_llm_output = generate_feedback_for_module(
                        system_prompt=populated_system_prompt,
                        user_prompt=populated_user_prompt,
                        model_name=args.model,
                        module_id=module_id,
                        user_name=user_name,
                        task_name=task_name,
                        temperature=args.temperature, # Pass temperature from args
                        output_model_name=output_model_name # Pass the Pydantic model name
                        # Pass other necessary LLM parameters from args or config if needed
                    )
                    all_module_outputs[module_id] = module_llm_output
                else:
                    logger.info(f"Skipping LLM call for module {module_id} for user {user_name} as --skip-feedback is set.")
                    all_module_outputs[module_id] = f"LLM processing skipped for module {module_id} (as per --skip-feedback)."
                
                # logger.debug(f"Populated prompt for module {module_id} for {user_name}:\n{populated_prompt}")
                # # For now, let's simulate an output
                # simulated_output = f"### LLM Output for Module: {module_id}\nInput data considered for {user_name}:\n"
                # for k, v in prompt_template_vars.items():
                #     if k in populated_prompt: # Only show vars that were likely used in the prompt
                #         simulated_output += f"  - {k}: {str(v)[:100] + '...' if len(str(v)) > 100 else str(v)}\n"
                # all_module_outputs[module_id] = simulated_output

            # 4. Assemble final report from module outputs
            final_report_content = ""
            report_structure_config = task_config.get('report_structure', {})
            
            # Header
            header_template = report_structure_config.get('header', "# Feedback for {task_name} - {user_name}\n")
            try:
                final_report_content += header_template.format(task_name=task_name, user_name=user_name, user_id=user_id)
            except KeyError as e:
                logger.warning(f"KeyError while formatting report header for {user_name} ({user_id}): {e}. Using basic header.")
                final_report_content += f"# Feedback for {task_name} - {user_name} ({user_id})\n"
            
            # Sections based on report_structure
            for section_config in report_structure_config.get('sections', []):
                module_id_for_section = section_config.get('module_id')
                section_title_template = section_config.get('title', "### Module: {module_id}\n")
                try:
                    section_title = section_title_template.format(module_id=module_id_for_section, task_name=task_name, user_name=user_name, user_id=user_id)
                except KeyError as e:
                    logger.warning(f"KeyError while formatting section title for module '{module_id_for_section}' for {user_name} ({user_id}): {e}. Using basic title.")
                    section_title = f"### Module: {module_id_for_section}"

                module_output = all_module_outputs.get(module_id_for_section, f"Content for module '{module_id_for_section}' not found or module failed.")
                
                final_report_content += f"\n{section_title}\n{module_output}\n"

            # Footer
            footer_template = report_structure_config.get('footer', "\n---\nEnd of feedback.")
            try:
                final_report_content += footer_template.format(task_name=task_name, user_name=user_name, user_id=user_id)
            except KeyError as e:
                logger.warning(f"KeyError while formatting report footer for {user_name} ({user_id}): {e}. Using basic footer.")
                final_report_content += f"\n---\nEnd of feedback for {user_name} ({user_id})."

            # 5. Save the assembled report
            if not args.skip_feedback: # Re-using this flag
                output_dir_base = Path(dirs['feedback'])
                if args.output_target == 'marker_report':
                    output_dir_base = Path(dirs['feedback'].parent / f"{task_name}_marker_reports")
                
                output_dir_base.mkdir(parents=True, exist_ok=True)
                
                file_extension = args.feedback_format if args.feedback_format != 'text' else 'txt'
                report_filename = f"{user_name.replace(' ', '_')}_{user_id}_{task_name}_modular_feedback.{file_extension}"
                report_file_path = output_dir_base / report_filename

                try:
                    with open(report_file_path, 'w', encoding='utf-8') as f:
                        f.write(final_report_content)
                    logger.info(f"Modular {args.output_target} generated: {report_file_path}")
                except IOError as e:
                    logger.error(f"Failed to write modular report to {report_file_path}: {e}")
            else:
                logger.info(f"Skipping modular feedback/report generation for {user_name} as requested.")

            logger.info(f"Successfully finished processing for user: {user_name} ({user_id}) on task {task_name}")

        except Exception as e:
            logger.error(f"Unhandled error processing user {user_name} ({user_id}) for task {task_name}: {str(e)}")
            logger.exception("Detailed error traceback:")
            # Continue processing next student

def main() -> int:
    """Main entry point for the marking pipeline."""
    args: Optional[argparse.Namespace] = None
    try:
        args = parse_args()
    except Exception as e:
        # Use basic logging if setup failed or hasn't happened yet
        logging.error(f"Error parsing arguments: {str(e)}") 
        return 1
    
    # Setup logging using parsed arguments
    # Do this early so subsequent messages are logged correctly
    setup_logging(args.log_level, args.log_file)
    
    # Validate inputs after logging is configured
    error = validate_inputs(args)
    if error:
        logger.error(f"Input validation failed: {error}")
        return 1
    
    # Log the start of processing with validated args
    logger.info("Starting MODULAR marking pipeline with arguments:")
    for arg, value in vars(args).items():
        logger.info(f"  {arg}: {value}")

    try:
        # Process the specified task
        process_task(args)
        logger.info(f"Pipeline completed processing for task: {args.task_name}")
        return 0
        
    except Exception as e:
        logger.critical(f"Pipeline failed during processing of task {args.task_name}: {str(e)}")
        logger.exception("Detailed pipeline error traceback:")
        return 1

if __name__ == '__main__':
    sys.exit(main()) 