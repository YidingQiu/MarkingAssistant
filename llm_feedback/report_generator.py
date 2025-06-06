import logging
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import yaml # For reading rubric/prompt configs
import re

from llm_feedback.test_result_analyzer import TestResultAnalyzer # Assuming this path
from .llm_deployment import LLMDeployment # Added LLMDeployment import

logger = logging.getLogger(__name__)

# Helper to load YAML config files (simplified)
def load_yaml_file(file_path_str: str) -> Optional[Dict]:
    try:
        file_path = Path(file_path_str)
        if not file_path.exists():
            logger.error(f"YAML file not found: {file_path_str}")
            return None
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading YAML file {file_path_str}: {e}")
        return None

def format_report_prompt(
    student_id: str,
    student_name: str,
    task_name: str,
    task_description: str,
    rubric_criteria: Dict,
    test_summary: Dict, 
    failed_tests_details: List[Dict],
    code_quality_issues: Dict, 
    source_code_snippets: Dict[str, str], 
    markdown_summaries: List[str],
    document_text_summaries: Dict[str, str],
    marker_report_output_template_str: str
) -> str:
    """Constructs the user-facing part of prompt for the LLM to generate a marker report."""
    
    user_message_parts = []

    user_message_parts.append(f"## Student Submission Details:")
    user_message_parts.append(f"- **Student Name**: {student_name}")
    user_message_parts.append(f"- **Student ID**: {student_id}")
    user_message_parts.append(f"- **Task Name**: {task_name}")
    user_message_parts.append(f"- **Task Description**: {task_description}")
    
    user_message_parts.append("\n## Rubric Criteria for Assessment (from marking_config.yaml):")
    # Iterate through problems_config (e.g., problem1, problem2)
    for problem_key, problem_config in rubric_criteria.items(): 
        problem_name = problem_config.get('name', problem_key.capitalize())
        problem_weight = problem_config.get('weight', 'N/A')
        problem_task_desc = problem_config.get('task_description', '')
        
        user_message_parts.append(f"\n### Problem: {problem_name} (Max Score: {problem_weight} pts)")
        if problem_task_desc:
            user_message_parts.append(f"  _Task Focus: {problem_task_desc}_")
        
        standard_tasks_list = problem_config.get('standard_tasks')
        if isinstance(standard_tasks_list, list) and standard_tasks_list:
            user_message_parts.append(f"  _Standard Requirements for {problem_name}:_")
            for i, task_item in enumerate(standard_tasks_list):
                user_message_parts.append(f"    {i+1}. {task_item}")
            user_message_parts.append("") # Add a blank line for spacing

        problem_criteria_dict = problem_config.get('criteria')
        if isinstance(problem_criteria_dict, dict):
            for criterion_key, criterion_details in problem_criteria_dict.items():
                criterion_name = criterion_key.replace('_', ' ').capitalize()
                points = criterion_details.get('points', 'N/A')
                description = criterion_details.get('description', 'No description.')
                user_message_parts.append(f"  - **{criterion_name} ({points} pts)**: {description}")
        else:
            user_message_parts.append(f"  - Note: Detailed criteria for {problem_name} not found in expected dictionary format in config.")

    user_message_parts.append("\n## Test Results Summary:")
    user_message_parts.append(f"- Overall Status: {'Passed' if test_summary.get('passed') else 'Failed'}")
    user_message_parts.append(f"- Total Tests: {test_summary.get('total_tests', 0)}, Passed: {test_summary.get('passed_tests', 0)}, Failed: {test_summary.get('failed_tests', 0)}")
    if failed_tests_details:
        user_message_parts.append("\n### Failed Tests Details (first 3):")
        for test in failed_tests_details[:3]:
            user_message_parts.append(f"- Test: {test.get('name', 'N/A')}\n  Error: {test.get('error_message', 'N/A')}")
            if test.get('context'):
                user_message_parts.append(f"  Context:\n{test.get('context')}")
    
    user_message_parts.append("\n## Code Quality Summary:")
    # Check if flake8 results exist and have issues
    flake8_results = code_quality_issues.get('flake8', {})
    if isinstance(flake8_results, dict) and flake8_results.get('has_issues'):
        user_message_parts.append(f"- Flake8 Issues: Yes. Output snippet:\n{flake8_results.get('output', '')[:300]}...")
    elif isinstance(flake8_results, dict) and 'output' in flake8_results : # It ran, no issues or just output
        user_message_parts.append(f"- Flake8: Output provided (may indicate no major issues or specific info):\n{flake8_results.get('output', '')[:150]}...")
    else: # Default if no specific flake8 data or not run
        user_message_parts.append("- Flake8: No specific issues reported or not run.")

    black_results = code_quality_issues.get('black', {})
    if isinstance(black_results, dict) and black_results.get('has_issues'):
        user_message_parts.append(f"- Black Formatting: Issues found. Output snippet:\n{black_results.get('output', '')[:300]}...")
    elif isinstance(black_results, dict) and 'output' in black_results:
        user_message_parts.append(f"- Black: Output provided (may indicate well-formatted or specific info):\n{black_results.get('output', '')[:150]}...")
    else:
        user_message_parts.append("- Black: No specific issues reported or not run.")

    if source_code_snippets:
        user_message_parts.append("\n## Relevant Source Code Snippets:")
        # Try to associate code snippets with problems if possible
        problem1_code_included = False
        problem2_code_included = False
        other_code_snippets = []

        for file_path_str, code in source_code_snippets.items():
            file_name = Path(file_path_str).name
            snippet = f"### From file: {file_name}\n```python\n{code[:700]}...\n```\n"
            # Basic heuristic to assign code to problems
            if "1" in problem_key_from_filename(file_name) and not problem1_code_included:
                user_message_parts.append("\n#### Source Code for Problem 1 (or related):")
                user_message_parts.append(snippet)
                problem1_code_included = True
            elif "2" in problem_key_from_filename(file_name) and not problem2_code_included:
                user_message_parts.append("\n#### Source Code for Problem 2 (or related):")
                user_message_parts.append(snippet)
                problem2_code_included = True
            else:
                other_code_snippets.append(snippet)
        
        if other_code_snippets:
            user_message_parts.append("\n#### Other Submitted Code Snippets:")
            for snippet in other_code_snippets:
                user_message_parts.append(snippet)

    if markdown_summaries:
        user_message_parts.append("\n## Student Explanations (from Markdown - first 2 snippets):")
        for i, md_summary in enumerate(markdown_summaries[:2]): 
            user_message_parts.append(f"- Explanation Snippet {i+1}: {md_summary[:300]}...")

    if document_text_summaries:
        user_message_parts.append("\n## Student Explanations (from Documents - first document):")
        for doc_name, text_summary in list(document_text_summaries.items())[:1]:
            user_message_parts.append(f"- From {doc_name}: {text_summary[:300]}...")
            
    user_message_parts.append("\n\n## Required Output Format for Your Report:")
    user_message_parts.append("Please fill in the details in the following markdown structure:")
    user_message_parts.append(marker_report_output_template_str)

    return "\n".join(user_message_parts)

# Helper function to extract problem key (e.g., "1", "2a") from filename
# This is a simplified version, might need to be more robust or aligned
# with get_problem_number from test_runner_main.py
def problem_key_from_filename(filename: str) -> str:
    match = re.search(r'_([12][a-zA-Z]?)\.(?:ipynb|py)', filename)
    if match:
        return match.group(1)
    match = re.search(r'Problem([12][a-zA-Z]?)', filename, re.IGNORECASE)
    if match:
        return match.group(1)
    if "1" in filename:
        return "1"
    if "2" in filename:
        return "2"
    return "unknown" # Fallback

class ReportGenerator:
    def __init__(self, model_name: str, config_base_dir: str = 'rubric'):
        self.llm = LLMDeployment(model_name)
        self.config_base_dir = Path(config_base_dir) # Store as Path object
        self.prompts_config = load_yaml_file(str(self.config_base_dir / 'feedback_prompt.yaml'))
        if not self.prompts_config:
            logger.error("Failed to load feedback_prompt.yaml. Marker reports may use default prompts.")
            self.prompts_config = {}
        
        # Load the marker report output template
        self.marker_report_output_template = load_yaml_file(str(self.config_base_dir / 'marker_report_template.yaml'))
        if not self.marker_report_output_template or 'marker_report_format' not in self.marker_report_output_template:
            logger.error("Failed to load marker_report_template.yaml or 'marker_report_format' key missing. Using basic fallback.")
            self.marker_report_output_template_str = "# Basic Marker Report\n## Score: [Score]\n## Justification: [Justification]"
        else:
            self.marker_report_output_template_str = self.marker_report_output_template['marker_report_format']

    def generate_single_report(
        self,
        results_json_path: Optional[str],
        flake8_json_path: Optional[str],
        black_json_path: Optional[str],
        task_name: str,
        report_dir_path: Path, # Changed to Path object
        source_code_dict: Optional[Dict[str, str]] = None, 
        markdown_content: Optional[List[str]] = None, 
        document_text: Optional[Dict[str, str]] = None
    ) -> None:
        logger.info(f"Marker report generation requested for task: {task_name}")
        if results_json_path: logger.info(f"Using test results: {results_json_path}")
        else: logger.warning("No test results JSON path provided, report will be limited.")

        test_analyzer = None
        test_summary_data = {'passed': False, 'total_tests': 0, 'passed_tests': 0, 'failed_tests': 0}
        failed_tests_details_data = []
        student_id_from_results = "UnknownStudent"
        student_name_from_results = "UnknownName"

        if results_json_path and Path(results_json_path).exists():
            try:
                test_analyzer = TestResultAnalyzer(results_json_path)
                if test_analyzer.metadata:
                    student_id_from_results = test_analyzer.metadata.student_id or student_id_from_results
                    student_name_from_results = test_analyzer.metadata.student_name or student_name_from_results
                
                total_p, passed_p, failed_p = 0,0,0
                for prob_id, prob_data in test_analyzer.problems.items():
                    if prob_data.test_results and 'summary' in prob_data.test_results:
                        ts = prob_data.test_results['summary']
                        total_p += ts.total_tests; passed_p += ts.passed_tests; failed_p += ts.failed_tests
                        if prob_data.test_results.get('details') and prob_data.test_results['details'].test_cases:
                            for tc_detail in prob_data.test_results['details'].test_cases:
                                if isinstance(tc_detail, dict) and tc_detail.get('status') == 'FAILED':
                                     failed_tests_details_data.append(tc_detail)
                test_summary_data.update({'total_tests': total_p, 'passed_tests': passed_p, 'failed_tests': failed_p, 'passed': failed_p == 0 and total_p > 0})
            except Exception as e:
                logger.error(f"Error analyzing test results from {results_json_path}: {e}")
        else:
            logger.warning(f"Test results file {results_json_path} not found or path not provided.")
            if results_json_path:
                 try:
                    parts = Path(results_json_path).stem.split('_')
                    if len(parts) >= 2: student_name_from_results = parts[0]; student_id_from_results = parts[1]
                 except: pass

        code_quality = {}
        for quality_path, key in [(flake8_json_path, 'flake8'), (black_json_path, 'black')]:
            if quality_path and Path(quality_path).exists():
                try:
                    with open(quality_path, 'r', encoding='utf-8') as f: quality_data_full = json.load(f)
                    if 'summary' in quality_data_full: code_quality[key] = quality_data_full['summary'] 
                    elif 'problems' in quality_data_full and quality_data_full['problems']:
                        first_problem_key = list(quality_data_full['problems'].keys())[0]
                        code_quality[key] = quality_data_full['problems'][first_problem_key].get(f'{key}_results', {})
                    else: code_quality[key] = {}
                except Exception as e: code_quality[key] = {'error': f'Failed to load {key} data: {e}'}
            else: code_quality[key] = {'note': f'{key} results not provided or file not found'}

        marking_config_full = load_yaml_file(str(self.config_base_dir / 'marking_config.yaml'))
        
        task_config_data = marking_config_full.get(task_name, {}) if marking_config_full else {}
        task_description = task_config_data.get('description', 'N/A')
        rubric_criteria_data = task_config_data.get('scoring_config', {})
        
        marker_report_prompt_config = self.prompts_config.get('marker_report_generation', {})
        system_prompt = marker_report_prompt_config.get('system_prompt')
        if not system_prompt:
            logger.error("'marker_report_generation.system_prompt' not found. Using basic fallback system prompt.")
            system_prompt = "You are an expert marker. Please review the student submission details and provide a marker report based on the provided output format template."
        
        user_message = format_report_prompt(
            student_id=student_id_from_results, 
            student_name=student_name_from_results,
            task_name=task_name, task_description=task_description,
            rubric_criteria=rubric_criteria_data, test_summary=test_summary_data, 
            failed_tests_details=failed_tests_details_data, code_quality_issues=code_quality,
            source_code_snippets=source_code_dict or {},
            markdown_summaries=markdown_content or [],
            document_text_summaries=document_text or {},
            marker_report_output_template_str=self.marker_report_output_template_str
        )
        
        logger.info(f"LLM System Prompt for Marker Report (student {student_id_from_results}):\n{system_prompt[:100]}...")
        logger.info(f"LLM User Message for Marker Report (student {student_id_from_results}):\n{user_message[:100]}...")
        
        llm_response_obj = self.llm.custom_analysis(data=user_message, system_prompt=system_prompt)
        llm_response_content = "Error generating LLM response for marker report."
        if llm_response_obj and llm_response_obj.success:
            llm_response_content = llm_response_obj.content
            logger.info("LLM call for marker report successful.")
        elif llm_response_obj: llm_response_content += f" Error: {llm_response_obj.error}"; logger.error(f"LLM call failed: {llm_response_obj.error}")
        else: logger.error("LLM call returned no response object.")

        report_file_name_base = f"{student_name_from_results.replace(' ', '_')}_{student_id_from_results}_{task_name.split('_')[0]}_{task_name.split('_')[1]}"
        report_file_name_base = report_file_name_base.replace(" ", "_").replace("(", "").replace(")", "").replace(":", "")[:100]
        report_file_path = report_dir_path / f"{report_file_name_base}_marker_report.md"
        
        try: report_dir_path.mkdir(parents=True, exist_ok=True)
        except Exception as e_mkdir: logger.error(f"Could not create report directory {report_dir_path}: {e_mkdir}"); return

        try:
            with open(report_file_path, 'w', encoding='utf-8') as f:
                f.write(llm_response_content)
            logger.info(f"Marker report saved to {report_file_path}")
        except Exception as e:
            logger.error(f"Failed to write marker report: {e}")

# Top-level function to be called by the pipeline
def generate_report(
    results_json_path: Optional[str],
    flake8_json_path: Optional[str],
    black_json_path: Optional[str],
    task_name: str,
    report_dir: str, # This will be string from pipeline
    model_name: str,
    source_code_dict: Optional[Dict[str, str]] = None, 
    markdown_content: Optional[List[str]] = None, 
    document_text: Optional[Dict[str, str]] = None,
    config_base_dir: str = 'rubric'
) -> None:
    report_dir_path = Path(report_dir) # Convert to Path object for internal use
    generator = ReportGenerator(model_name=model_name, config_base_dir=config_base_dir)
    generator.generate_single_report(
        results_json_path=results_json_path,
        flake8_json_path=flake8_json_path,
        black_json_path=black_json_path,
        task_name=task_name,
        report_dir_path=report_dir_path,
        source_code_dict=source_code_dict,
        markdown_content=markdown_content,
        document_text=document_text
    )

# Need to import Path from pathlib if not already done globally
from pathlib import Path 