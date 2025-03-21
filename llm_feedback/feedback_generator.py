from pathlib import Path
from typing import Dict, List, Optional, Literal
import json
import os
from dataclasses import dataclass
import logging
from .test_result_analyzer import TestResultAnalyzer
from .llm_deployment import LLMDeployment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supported feedback formats
FeedbackFormat = Literal["html", "markdown", "text"]


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
        
        # Create feedback directory if it doesn't exist
        self.feedback_dir.mkdir(parents=True, exist_ok=True)

    def _read_source_code(self, file_path: str) -> Optional[str]:
        """Read source code from file.
        
        Args:
            file_path: Path to the source code file
            
        Returns:
            Source code content or None if file not found
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
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
            # Get problem analysis
            problem_analysis = self.test_analyzer.get_problem_analysis(problem_id)
            
            # Read source code
            source_code = self._read_source_code(
                self.test_analyzer.problems[problem_id].solution_path
            )
            
            # Prepare data for LLM
            analysis_data = {
                "problem_id": problem_id,
                "test_results": problem_analysis,
                "source_code": source_code,
                "code_quality": self.test_analyzer.problems[problem_id].code_quality,
                "student_info": self.test_analyzer.get_submission_summary()["student"]
            }
            
            # Generate feedback using LLM
            system_prompt = f"""You are an expert programming instructor providing detailed feedback for a student's code submission.
            Generate feedback in {self.feedback_format.upper()} format.
            Focus on:
            1. Test results analysis and specific test cases
            2. Code quality and style issues
            3. Specific suggestions for improvement
            4. Positive aspects of the implementation
            """
            
            llm_response = self.llm.custom_analysis(
                data=analysis_data,
                system_prompt=system_prompt
            )
            
            if not llm_response.success:
                raise Exception(f"LLM analysis failed: {llm_response.error}")
            
            # Format feedback
            formatted_feedback = self._format_feedback(
                llm_response.content,
                self.feedback_format
            )
            
            return QuestionFeedback(
                problem_id=problem_id,
                feedback_content=formatted_feedback,
                format=self.feedback_format,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Error generating feedback for problem {problem_id}: {str(e)}")
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
        # Create student-specific directory
        student_info = self.test_analyzer.get_submission_summary()["student"]
        student_dir = self.feedback_dir / f"{student_info['id']}_{student_info['lab']}"
        student_dir.mkdir(parents=True, exist_ok=True)
        
        # Save individual problem feedback
        for problem_id, prob_feedback in feedback.items():
            if not prob_feedback.success:
                logger.error(f"Skipping saving feedback for problem {problem_id} due to generation error")
                continue
                
            file_extension = {
                "html": ".html",
                "markdown": ".md",
                "text": ".txt"
            }[prob_feedback.format]
            
            feedback_file = student_dir / f"problem_{problem_id}{file_extension}"
            
            try:
                with open(feedback_file, 'w', encoding='utf-8') as f:
                    f.write(prob_feedback.feedback_content)
                logger.info(f"Saved feedback for problem {problem_id} to {feedback_file}")
            except Exception as e:
                logger.error(f"Error saving feedback for problem {problem_id}: {str(e)}")
        
        # Generate and save summary feedback
        try:
            summary_data = {
                "student_info": student_info,
                "overall_results": self.test_analyzer.get_submission_summary(),
                "individual_feedback_files": [f.name for f in student_dir.glob(f"*{file_extension}")]
            }
            
            summary_response = self.llm.custom_analysis(
                data=summary_data,
                system_prompt=f"""Generate a summary of the student's overall performance in {self.feedback_format.upper()} format.
                Include links to individual problem feedback files and highlight key areas of strength and improvement."""
            )
            
            if summary_response.success:
                summary_file = student_dir / f"summary{file_extension}"
                with open(summary_file, 'w', encoding='utf-8') as f:
                    f.write(self._format_feedback(summary_response.content, self.feedback_format))
                logger.info(f"Saved feedback summary to {summary_file}")
        except Exception as e:
            logger.error(f"Error generating/saving feedback summary: {str(e)}")


def generate_feedback(results_json_path: str,
                     feedback_dir: str = "feedback",
                     model_name: str = "qwq",
                     feedback_format: FeedbackFormat = "html") -> None:
    """Convenience function to generate feedback for a submission.
    
    Args:
        results_json_path: Path to the test results JSON file
        feedback_dir: Directory to store generated feedback
        model_name: Name of the LLM model to use
        feedback_format: Format of the generated feedback
    """
    generator = FeedbackGenerator(
        results_json_path=results_json_path,
        feedback_dir=feedback_dir,
        model_name=model_name,
        feedback_format=feedback_format
    )
    
    feedback = generator.generate_all_feedback()
    generator.save_feedback(feedback)
