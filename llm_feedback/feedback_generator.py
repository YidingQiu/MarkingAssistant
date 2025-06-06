from pathlib import Path
from typing import Dict, List, Optional, Literal, Any
import json
import os
import yaml
from dataclasses import dataclass
import logging
import re
from .test_result_analyzer import TestResultAnalyzer
from .llm_deployment import LLMDeployment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supported feedback formats
FeedbackFormat = Literal["html", "markdown", "text"]

# Load prompts from YAML
def load_prompts() -> Dict:
    """Load prompts from YAML file."""
    prompts_path = Path(__file__).parent.parent / "rubric" / "feedback_prompt.yaml"
    if not prompts_path.exists():
        logger.error(f"Prompts file not found: {prompts_path}. Using default prompts if available.")
        return {'feedback_generation': {'system_prompt': 'Provide feedback'}, 'summary_generation': {'system_prompt': 'Summarize feedback'}} 
    
    try:
        with open(prompts_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except yaml.YAMLError as e:
        logger.error(f"Error parsing prompts file {prompts_path}: {e}. Using default prompts.")
        return {'feedback_generation': {'system_prompt': 'Provide feedback'}, 'summary_generation': {'system_prompt': 'Summarize feedback'}} 

# Load prompts once at module level
PROMPTS = load_prompts()


@dataclass
class QuestionFeedback:
    """Feedback for a single question."""
    problem_id: str
    feedback_content: str
    format: FeedbackFormat
    success: bool
    error: Optional[str] = None


class FeedbackGenerator:
    """Generates detailed feedback for student submissions."""
    
    def __init__(self, 
                 results_json_path: Optional[str],
                 flake8_json_path: Optional[str],
                 black_json_path: Optional[str],
                 task_name: str,
                 feedback_dir: str = "feedback",
                 model_name: str = "qwq",
                 feedback_format: FeedbackFormat = "html",
                 exclude_tools: List[str] = None,
                 source_code_dict: Optional[Dict[str, str]] = None,
                 markdown_content: Optional[List[str]] = None,
                 document_text: Optional[Dict[str, str]] = None):
        """Initialize feedback generator.
        
        Args:
            results_json_path: Path to the test results JSON file
            flake8_json_path: Path to the Flake8 results JSON file
            black_json_path: Path to the Black results JSON file
            task_name: The name of the task being processed.
            feedback_dir: Directory to store generated feedback
            model_name: Name of the LLM model to use
            feedback_format: Format of the generated feedback (html/markdown/text)
            exclude_tools: List of code quality tools to exclude from feedback (e.g., ['black', 'flake8'])
            source_code_dict: Dictionary of source code for each problem
            markdown_content: List of markdown content for each problem
            document_text: Dictionary of document text for each problem
        """
        self.results_json_path = Path(results_json_path) if results_json_path else None
        self.flake8_json_path = Path(flake8_json_path) if flake8_json_path else None
        self.black_json_path = Path(black_json_path) if black_json_path else None
        self.task_name = task_name
        self.feedback_dir_base = Path(feedback_dir)
        self.feedback_format = feedback_format
        self.exclude_tools = exclude_tools or []
        self.source_code_dict = source_code_dict or {}
        self.markdown_content = markdown_content or []
        self.document_text = document_text or {}
        
        self.test_analyzer = None
        if self.results_json_path and self.results_json_path.exists():
            try:
                self.test_analyzer = TestResultAnalyzer(str(self.results_json_path))
            except Exception as e:
                logger.error(f"Failed to initialize TestResultAnalyzer for {self.results_json_path}: {e}")
                # self.test_analyzer remains None, subsequent methods should handle this
        else:
            logger.warning(f"Results JSON path not provided or file does not exist: {self.results_json_path}. Test-based feedback will be limited.")
        
        self.llm = LLMDeployment(model_name)
        self.feedback_dir = self.feedback_dir_base
        try:
            self.feedback_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured feedback directory exists: {self.feedback_dir}")
        except Exception as e:
             logger.error(f"Could not create feedback directory {self.feedback_dir}: {e}. Feedback might not be saved.")

    def _read_source_code_from_dict(self, problem_id_or_file_key: str) -> Optional[str]:
        """Retrieve source code for a specific problem/file from the preloaded dict."""
        # This assumes problem_id can be mapped to a key in self.source_code_dict
        # or that source_code_dict keys are the full paths from ProblemResult.solution_path
        # We need a consistent way to link problem_id to the right code file.
        # For now, let's assume problem_id might correspond to a main notebook/script for that problem.
        
        # Try finding a direct match if problem_id_or_file_key is a full path
        if problem_id_or_file_key in self.source_code_dict:
            return self.source_code_dict[problem_id_or_file_key]

        # If problem_id is just a number (e.g., "1", "2a"), try to find a matching file
        # This is a heuristic and might need refinement based on file naming conventions
        for file_path, code in self.source_code_dict.items():
            # Example: if problem_id is "1" and file_path contains "Problem1" or "_1.ipynb"
            if f"_{problem_id_or_file_key}.py" in file_path or \
               f"_{problem_id_or_file_key}.ipynb" in file_path or \
               f"Problem{problem_id_or_file_key}." in file_path or \
               f"problem{problem_id_or_file_key}." in file_path:
                logger.info(f"Matched problem_id '{problem_id_or_file_key}' to source file: {file_path}")
                return code
        
        if self.source_code_dict: # If dict is not empty but no match found
             logger.warning(f"Could not find source code for problem/file key '{problem_id_or_file_key}' in preloaded source_code_dict. Keys: {list(self.source_code_dict.keys())}")
        # else: source_code_dict was empty to begin with
        return "[Source code for this specific problem was not uniquely identified or provided.]"

    def _format_feedback(self, content: str, format: FeedbackFormat) -> str:
        """Format feedback content according to specified format."""
        content_str = str(content if content is not None else "")
        
        if format == "html":
            html_content = content_str.replace('\n', '<br>\n')
            html_content = html_content.replace('```python', '<pre><code>').replace('```', '</code></pre>')
            
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Feedback</title>
                <style>
                    body {{ font-family: sans-serif; line-height: 1.6; max-width: 900px; margin: 20px auto; padding: 15px; border: 1px solid #ccc; border-radius: 8px; }}
                    h1, h2, h3 {{ color: #333; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
                    .feedback-section {{ margin-bottom: 25px; padding: 15px; border: 1px solid #eee; border-radius: 5px; background-color: #f9f9f9; }}
                    .success {{ color: green; font-weight: bold; }}
                    .warning {{ color: orange; font-weight: bold; }}
                    .error {{ color: red; font-weight: bold; }}
                    pre {{ background-color: #f0f0f0; padding: 10px; border-radius: 5px; overflow-x: auto; white-space: pre-wrap; word-wrap: break-word; }}
                    code {{ font-family: monospace; }}
                </style>
            </head>
            <body>
                <h1>Feedback Report</h1>
                {html_content}
            </body>
            </html>
            """
        elif format == "markdown":
            return content_str
        else:
            text_content = re.sub(r'<[^>]+>', '', content_str)
            text_content = text_content.replace('**', '').replace('*', '').replace('__', '').replace('_', '')
            text_content = text_content.replace('``', '').replace('`', '')
            text_content = text_content.replace('#', '')
            return text_content

    def generate_question_feedback(self, problem_id: str) -> QuestionFeedback:
        """Generate feedback for a single question."""
        try:
            logger.info(f"Starting feedback generation for problem {problem_id}")
            
            problem_data = None
            problem_analysis_dict = {}
            code_quality_dict = {}
            student_metadata_info = {}

            if self.test_analyzer and self.test_analyzer.problems:
                problem_data = self.test_analyzer.problems.get(problem_id)
                if self.test_analyzer.metadata:
                    student_metadata_info = self.test_analyzer.metadata.to_dict() # if it has to_dict

            if problem_data:
                if problem_data.test_results:
                    problem_analysis_dict = {
                        'summary': problem_data.test_results.get('summary').to_dict() if hasattr(problem_data.test_results.get('summary'), 'to_dict') else problem_data.test_results.get('summary'),
                        'details': problem_data.test_results.get('details').to_dict() if hasattr(problem_data.test_results.get('details'), 'to_dict') else problem_data.test_results.get('details')
                    }
                if problem_data.code_quality: # Assuming code_quality might be directly on problem_data now
                    quality_data = problem_data.code_quality.to_dict() if hasattr(problem_data.code_quality, 'to_dict') else {}
                    if 'tool_results' in quality_data:
                        quality_data['tool_results'] = {tool: result for tool, result in quality_data['tool_results'].items() if tool.lower() not in self.exclude_tools}
                        quality_data['tools_run'] = [tool for tool in quality_data.get('tools_run', []) if tool.lower() not in self.exclude_tools]
                        quality_data['has_quality_issues'] = any(r.get('has_issues', False) for r in quality_data['tool_results'].values())
                    code_quality_dict = quality_data
            else:
                logger.warning(f"No specific test analysis data found for problem {problem_id} in results file. Feedback may be limited.")
                problem_analysis_dict = {'summary': {'status': 'No test data'}, 'details': {'full_output': 'Test data not available for this problem.'}}

            # Load flake8/black quality if paths provided (and not already in problem_data)
            # This part might be redundant if marking_pipeline passes them directly or if TestResultAnalyzer integrates them.
            # For now, assuming they might come from separate files if test_analyzer didn't load them.
            if not code_quality_dict.get('flake8') and self.flake8_json_path and self.flake8_json_path.exists():
                try:
                    with open(self.flake8_json_path, 'r') as f: flake8_data = json.load(f)
                    code_quality_dict['flake8'] = flake8_data.get('problems', {}).get(problem_id, {}).get('flake8_results', {'output': 'Flake8 data not found for problem.'})
                except Exception as e: logger.error(f"Error loading Flake8 data for problem {problem_id}: {e}")
            
            if not code_quality_dict.get('black') and self.black_json_path and self.black_json_path.exists():
                try:
                    with open(self.black_json_path, 'r') as f: black_data = json.load(f)
                    code_quality_dict['black'] = black_data.get('problems', {}).get(problem_id, {}).get('black_results', {'output': 'Black data not found for problem.'})
                except Exception as e: logger.error(f"Error loading Black data for problem {problem_id}: {e}")

            # Get the specific source code for this problem
            source_code_for_problem = self._read_source_code_from_dict(problem_id) 
            # If problem_id is not a direct key, try to find by solution_path if available in problem_data
            if source_code_for_problem == "[Source code for this specific problem was not uniquely identified or provided.]" and problem_data and problem_data.solution_path:
                source_code_for_problem = self._read_source_code_from_dict(str(problem_data.solution_path))

            analysis_data = {
                "problem_id": problem_id,
                "test_results": problem_analysis_dict,
                "source_code": source_code_for_problem,
                "code_quality": code_quality_dict,
                "student_info": student_metadata_info, # Use overall student info
                "student_markdown": "\n---\n".join(self.markdown_content), # Combine all markdown for now
                "student_documents": self.document_text # Pass the dict of doc_name: text_content
            }
            
            logger.debug(f"Analysis data prepared for LLM: {json.dumps(analysis_data, indent=2)}")
            
            feedback_prompt_config = PROMPTS.get('feedback_generation', {})
            system_prompt_template = feedback_prompt_config.get('system_prompt', "Provide feedback in {format} format.")
            system_prompt = system_prompt_template.format(format=self.feedback_format.upper())
            
            logger.info(f"Generating LLM feedback for problem {problem_id}...")
            llm_response = self.llm.custom_analysis(
                data=analysis_data,
                system_prompt=system_prompt
            )
            
            if not llm_response or not llm_response.success:
                err_msg = llm_response.error if llm_response else "Unknown LLM error"
                logger.error(f"LLM analysis failed for problem {problem_id}: {err_msg}")
                raise Exception(f"LLM analysis failed: {err_msg}")
            
            logger.info(f"LLM feedback received for problem {problem_id}. Formatting...")
            formatted_feedback = self._format_feedback(
                llm_response.content,
                self.feedback_format
            )
            
            logger.info(f"Successfully generated feedback for problem {problem_id}")
            return QuestionFeedback(
                problem_id=problem_id,
                feedback_content=formatted_feedback,
                format=self.feedback_format,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error generating feedback for problem {problem_id}: {str(e)}", exc_info=True)
            return QuestionFeedback(
                problem_id=problem_id,
                feedback_content=f"Error generating feedback: {str(e)}",
                format=self.feedback_format,
                success=False,
                error=str(e)
            )

    def generate_all_feedback(self) -> Dict[str, QuestionFeedback]:
        """Generate feedback for all questions in the submission."""
        all_feedback: Dict[str, QuestionFeedback] = {}
        if not self.test_analyzer or not hasattr(self.test_analyzer, 'problems') or not self.test_analyzer.problems:
             logger.warning(f"No problems found in analyzer or analyzer not initialized. Path: {self.results_json_path}. Feedback generation will be skipped for problem-specific parts.")
             # Still, we might have general markdown/document text to summarize for an overall feedback
             # If there are no problems from tests, but we have other content, we could generate a general feedback here.
             # For now, if no problems from tests, it returns empty dict.
             if not self.source_code_dict and not self.markdown_content and not self.document_text:
                return all_feedback # Truly nothing to process
             else: # Process general feedback if other content exists
                # This assumes a generic problem_id like "general" or that generate_question_feedback can handle no test_analyzer data
                # For simplicity, let's assume generate_question_feedback is robust enough to handle missing test_analyzer.problems[problem_id]
                # This part needs careful design: how to provide feedback if only text/markdown is present without test results?
                # Maybe create a dummy problem_id = "Overall Submission Comments"
                logger.info("No test problems, but other content found. Attempting general feedback summary if possible.")
                # This path is not fully fleshed out. Returning empty for now if no problems.
                return all_feedback

        for problem_id in self.test_analyzer.problems.keys():
            feedback = self.generate_question_feedback(problem_id)
            all_feedback[problem_id] = feedback
        return all_feedback

    def save_feedback(self, feedback: Dict[str, QuestionFeedback]) -> None:
        """Save generated feedback to files."""
        student_name = "UnknownStudent"
        student_id = "UnknownID"
        if self.test_analyzer and self.test_analyzer.metadata:
            s_info = self.test_analyzer.metadata.student_info
            student_name = s_info.get('name', student_name).replace(' ', '_') if s_info else student_name.replace(' ', '_')
            student_id = s_info.get('id', student_id) if s_info else student_id
        elif self.results_json_path: # Try to get from filename if metadata not loaded
            try:
                parts = self.results_json_path.stem.split('_')
                if len(parts) >=2 :
                    student_name = parts[0].replace(' ', '_')
                    student_id = parts[1]
            except Exception: # Keep defaults if parsing filename fails
                pass 

        feedback_filename = f"{student_name}_{student_id}_{self.task_name}_feedback.{self.feedback_format}"
        feedback_file_path = self.feedback_dir / feedback_filename
        
        try:
            logger.info(f"Preparing to save feedback to: {feedback_file_path}")
            overall_summary_dict = {}
            if self.test_analyzer and hasattr(self.test_analyzer, 'get_submission_summary'):
                overall_summary_dict = self.test_analyzer.get_submission_summary()
            
            # Data for summary LLM call
            summary_llm_data = {
                "student_info": {"name": student_name, "id": student_id}, # Use parsed/defaulted name and ID
                "overall_results": overall_summary_dict,
                "problem_feedback_snippets": { # Provide snippets for summary context
                    pid: fb.feedback_content[:500] + "..." 
                    for pid, fb in feedback.items() if fb.success
                },
                "student_markdown_summary": ("\n---\n".join(self.markdown_content))[:1000] + "..." if self.markdown_content else "Not provided.",
                "student_documents_summary": { 
                    doc_name: text[:500] + "..." 
                    for doc_name, text in list(self.document_text.items())[:2] # First 2 docs, 500 chars each
                } if self.document_text else "Not provided."
            }
            
            summary_prompt_config = PROMPTS.get('summary_generation', {})
            system_prompt_template = summary_prompt_config.get('system_prompt', "Summarize feedback in {format} format.")
            system_prompt = system_prompt_template.format(format=self.feedback_format.upper())

            logger.info("Generating summary feedback using LLM...")
            summary_response = self.llm.custom_analysis(
                data=summary_llm_data,
                system_prompt=system_prompt
            )
            
            final_content_parts = []
            if summary_response and summary_response.success:
                logger.info("Summary generation successful.")
                final_content_parts.append(summary_response.content)
            else:
                err_msg = summary_response.error if summary_response else "Unknown LLM error during summary"
                logger.error(f"Failed to generate summary feedback: {err_msg}.")
                if self.feedback_format == "html":
                    final_content_parts.append("<h1>Feedback Report (Summary Generation Failed)</h1>")
                else:
                    final_content_parts.append("## Feedback Report (Summary Generation Failed)\n")
            
            # Append individual problem feedback
            for problem_id, fb_obj in feedback.items():
                if self.feedback_format == "html":
                    final_content_parts.append(f"<div class=\"feedback-section\"><h2>Problem: {problem_id}</h2>{fb_obj.feedback_content}</div>")
                elif self.feedback_format == "markdown":
                    final_content_parts.append(f"\n## Problem: {problem_id}\n\n{fb_obj.feedback_content}")
                else: # text
                    final_content_parts.append(f"\n--- Problem: {problem_id} ---\n{fb_obj.feedback_content}")
            
            full_feedback_content = "\n".join(final_content_parts)
            # Final formatting pass for the entire content
            final_formatted_output = self._format_feedback(full_feedback_content, self.feedback_format)

            with open(feedback_file_path, 'w', encoding='utf-8') as f:
                f.write(final_formatted_output)
            logger.info(f"Saved feedback to {feedback_file_path}")
                
        except Exception as e:
            logger.error(f"Error generating/saving feedback summary: {e}", exc_info=True)

def generate_feedback(
    results_json_path: Optional[str],
    flake8_json_path: Optional[str],
    black_json_path: Optional[str],
    task_name: str,
    feedback_dir: str = "feedback",
    model_name: str = "qwq",
    feedback_format: FeedbackFormat = "html",
    exclude_tools: Optional[List[str]] = None,
    source_code_dict: Optional[Dict[str, str]] = None, 
    markdown_content: Optional[List[str]] = None, 
    document_text: Optional[Dict[str, str]] = None
) -> None:
    """Generate feedback for a test results file.
    
    Args:
        results_json_path: Path to the test results JSON file
        flake8_json_path: Path to the Flake8 results JSON file
        black_json_path: Path to the Black results JSON file
        task_name: The name of the task being processed.
        feedback_dir: Directory to store generated feedback
        model_name: Name of the LLM model to use
        feedback_format: Format of the generated feedback (html/markdown/text)
        exclude_tools: List of code quality tools to exclude from feedback (e.g., ['black', 'flake8'])
        source_code_dict: Dictionary of source code for each problem
        markdown_content: List of markdown content for each problem
        document_text: Dictionary of document text for each problem
    """
    logger.info(f"Initiating feedback for task '{task_name}' (results: {results_json_path})")
    generator = FeedbackGenerator(
        results_json_path=results_json_path,
        flake8_json_path=flake8_json_path,
        black_json_path=black_json_path,
        task_name=task_name,
        feedback_dir=feedback_dir,
        model_name=model_name,
        feedback_format=feedback_format,
        exclude_tools=exclude_tools or [],
        source_code_dict=source_code_dict,
        markdown_content=markdown_content,
        document_text=document_text
    )
    
    logger.info("Generating feedback for all problems...")
    feedback = generator.generate_all_feedback()
    
    logger.info("Saving generated feedback...")
    generator.save_feedback(feedback)
    logger.info(f"Feedback process completed for task '{task_name}'.")
