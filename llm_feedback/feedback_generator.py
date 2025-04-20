from pathlib import Path
from typing import Dict, List, Optional, Literal
import json
import os
import yaml
from dataclasses import dataclass
import logging
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
    prompts_path = Path("rubric/feedback_prompt.yaml")
    if not prompts_path.exists():
        raise FileNotFoundError(f"Prompts file not found: {prompts_path}")
    
    with open(prompts_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

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
                 results_json_path: str,
                 feedback_dir: str = "feedback",
                 model_name: str = "qwq",
                 feedback_format: FeedbackFormat = "html"):
        """Initialize feedback generator.
        
        Args:
            results_json_path: Path to the test results JSON file
            feedback_dir: Directory to store generated feedback
            model_name: Name of the LLM model to use
            feedback_format: Format of the generated feedback (html/markdown/text)
        """
        self.results_json_path = Path(results_json_path)
        self.feedback_dir = Path(feedback_dir)
        self.feedback_format = feedback_format
        
        # Initialize analyzers
        self.test_analyzer = TestResultAnalyzer(str(results_json_path))
        self.llm = LLMDeployment(model_name)
        
        # Create lab-specific feedback directory
        lab_number = self.test_analyzer.metadata.lab_number
        self.feedback_dir = self.feedback_dir / f'Lab{lab_number}'
        self.feedback_dir.mkdir(parents=True, exist_ok=True)

    def _read_source_code(self, file_path: str) -> Optional[str]:
        """Read source code from file.
        
        Args:
            file_path: Path to the source code file
            
        Returns:
            Source code content or None if file not found
        """
        try:
            # Convert to Path object and resolve to handle any relative paths
            path = Path(file_path).resolve()
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading source code from {file_path}: {str(e)}")
            return None

    def _format_feedback(self, content: str, format: FeedbackFormat) -> str:
        """Format feedback content according to specified format.
        
        Args:
            content: Raw feedback content
            format: Desired format (html/markdown/text)
            
        Returns:
            Formatted feedback content
        """
        if format == "html":
            # Add HTML wrapper and style
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }}
                    h1, h2, h3 {{ color: #2c3e50; }}
                    .feedback-section {{ margin-bottom: 20px; padding: 15px; border: 1px solid #eee; border-radius: 5px; }}
                    .success {{ color: #27ae60; }}
                    .warning {{ color: #e67e22; }}
                    .error {{ color: #c0392b; }}
                    code {{ background-color: #f8f9fa; padding: 2px 4px; border-radius: 4px; }}
                </style>
            </head>
            <body>
                {content}
            </body>
            </html>
            """
        elif format == "markdown":
            # Return as is, assuming LLM generated markdown
            return content
        else:
            # Strip any markdown/HTML for plain text
            # This is a simple stripping, you might want to use a proper HTML/markdown stripper
            return content.replace("#", "").replace("*", "").replace("`", "")

    def generate_question_feedback(self, problem_id: str) -> QuestionFeedback:
        """Generate feedback for a single question.
        
        Args:
            problem_id: ID of the problem to generate feedback for
            
        Returns:
            QuestionFeedback object containing the feedback
        """
        try:
            logger.info(f"Starting feedback generation for problem {problem_id}")
            
            # Get problem analysis
            logger.info(f"Getting problem analysis for {problem_id}")
            problem_analysis = self.test_analyzer.get_problem_analysis(problem_id)
            logger.debug(f"Problem analysis: {problem_analysis}")
            
            # Read source code
            logger.info(f"Reading source code for problem {problem_id}")
            source_path = self.test_analyzer.problems[problem_id].solution_path
            logger.debug(f"Source code path: {source_path}")
            source_code = self._read_source_code(source_path)
            
            # Get code quality data
            logger.info(f"Getting code quality data for problem {problem_id}")
            code_quality = self.test_analyzer.problems[problem_id].code_quality
            logger.debug(f"Code quality object type: {type(code_quality)}")
            code_quality_dict = code_quality.to_dict()
            logger.debug(f"Code quality dict: {code_quality_dict}")
            
            # Get student info
            logger.info("Getting student info")
            student_info = self.test_analyzer.get_submission_summary()["student"]
            logger.debug(f"Student info: {student_info}")
            
            # Prepare data for LLM
            logger.info("Preparing analysis data for LLM")
            analysis_data = {
                "problem_id": problem_id,
                "test_results": problem_analysis,
                "source_code": source_code,
                "code_quality": code_quality_dict,
                "student_info": student_info
            }
            logger.debug(f"Analysis data prepared: {analysis_data}")
            
            # Generate feedback using LLM
            logger.info("Generating feedback using LLM")
            system_prompt = PROMPTS['feedback_generation']['system_prompt'].format(format=self.feedback_format.upper())
            
            llm_response = self.llm.custom_analysis(
                data=analysis_data,
                system_prompt=system_prompt
            )
            
            if not llm_response.success:
                logger.error(f"LLM analysis failed: {llm_response.error}")
                raise Exception(f"LLM analysis failed: {llm_response.error}")
            
            logger.info("LLM analysis successful, formatting feedback")
            # Format feedback
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
            logger.error(f"Error generating feedback for problem {problem_id}: {str(e)}")
            logger.exception("Detailed error traceback:")
            return QuestionFeedback(
                problem_id=problem_id,
                feedback_content="",
                format=self.feedback_format,
                success=False,
                error=str(e)
            )

    def generate_all_feedback(self) -> Dict[str, QuestionFeedback]:
        """Generate feedback for all questions in the submission.
        
        Returns:
            Dictionary mapping problem IDs to their feedback
        """
        all_feedback = {}
        for problem_id in self.test_analyzer.problems.keys():
            feedback = self.generate_question_feedback(problem_id)
            all_feedback[problem_id] = feedback
        return all_feedback

    def save_feedback(self, feedback: Dict[str, QuestionFeedback]) -> None:
        """Save generated feedback to files.
        
        Args:
            feedback: Dictionary mapping problem IDs to their feedback
        """
        # Get student info for filename
        student_info = self.test_analyzer.get_submission_summary()["student"]
        
        # Create feedback filename with same pattern as input
        feedback_file = self.feedback_dir / f"{student_info['name']}_{student_info['id']}_Lab{student_info['lab']}_feedback.{self.feedback_format}"
        
        try:
            # Generate summary feedback
            summary_data = {
                "student_info": student_info,
                "overall_results": self.test_analyzer.get_submission_summary(),
                "problem_feedback": {}
            }
            
            # Add individual problem feedback
            for problem_id, prob_feedback in feedback.items():
                if not prob_feedback.success:
                    logger.error(f"Skipping problem {problem_id} due to generation error")
                    continue
                summary_data["problem_feedback"][problem_id] = prob_feedback.feedback_content
            
            # Generate summary using LLM
            summary_response = self.llm.custom_analysis(
                data=summary_data,
                system_prompt=PROMPTS['summary_generation']['system_prompt'].format(format=self.feedback_format.upper())
            )
            
            if summary_response.success:
                with open(feedback_file, 'w', encoding='utf-8') as f:
                    f.write(self._format_feedback(summary_response.content, self.feedback_format))
                logger.info(f"Saved feedback to {feedback_file}")
            else:
                logger.error(f"Failed to generate summary feedback: {summary_response.error}")
                
        except Exception as e:
            logger.error(f"Error generating/saving feedback: {str(e)}")


def generate_feedback(results_json_path: str,
                     feedback_dir: str = "feedback",
                     model_name: str = "qwq",
                     feedback_format: FeedbackFormat = "html") -> None:
    """Generate feedback for a test results file.
    
    Args:
        results_json_path: Path to the test results JSON file
        feedback_dir: Directory to store generated feedback
        model_name: Name of the LLM model to use
        feedback_format: Format of the generated feedback (html/markdown/text)
    """
    # Initialize feedback generator
    generator = FeedbackGenerator(
        results_json_path=results_json_path,
        feedback_dir=feedback_dir,
        model_name=model_name,
        feedback_format=feedback_format
    )
    
    # Generate feedback for all problems
    feedback = generator.generate_all_feedback()
    
    # Save feedback
    generator.save_feedback(feedback)
