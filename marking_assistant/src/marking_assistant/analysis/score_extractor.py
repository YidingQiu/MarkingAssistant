import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
import re

logger = logging.getLogger(__name__)


class ModuleScore(BaseModel):
    """Individual module score information."""
    module_id: str = Field(description="The module identifier")
    score: float = Field(description="The score awarded for this module", ge=0)
    max_score: float = Field(description="The maximum possible score for this module", ge=0)
    justification: str = Field(description="The justification for the score")
    success: bool = Field(description="Whether the module was successfully evaluated")


class StudentScoreSummary(BaseModel):
    """Complete score summary for a student."""
    student_id: str = Field(description="The student identifier")
    student_name: Optional[str] = Field(None, description="The student name if available")
    task_name: str = Field(description="The task/assignment name")
    total_score: float = Field(description="Total score across all modules", ge=0)
    max_total_score: float = Field(description="Maximum possible total score", ge=0)
    percentage: float = Field(description="Percentage score", ge=0, le=100)
    module_scores: List[ModuleScore] = Field(description="Individual module scores")
    extraction_errors: List[str] = Field(default_factory=list, description="Any errors during extraction")


class ScoreExtractor:
    """Extracts and aggregates scores from intermediate response files."""
    
    def __init__(self, model_name: str = "openai:gpt-4o-mini"):
        """Initialize the score extractor."""
        self.model_name = model_name
    
    def extract_score_from_response(self, response_content: str, module_id: str, 
                                  max_score_hint: Optional[float] = None) -> ModuleScore:
        """Extract score information from a single response using direct parsing."""
        try:
            # Parse the response content if it's JSON
            if response_content.strip().startswith('{'):
                response_data = json.loads(response_content)
                
                # Direct extraction if it's already structured
                if isinstance(response_data, dict) and 'score' in response_data:
                    return ModuleScore(
                        module_id=module_id,
                        score=float(response_data.get('score', 0)),
                        max_score=max_score_hint or self._infer_max_score(response_content, module_id),
                        justification=response_data.get('justification', 'No justification provided'),
                        success=True
                    )
            
            # Fallback: try to extract score from text content
            score, justification = self._extract_score_from_text(response_content)
            max_score = max_score_hint or self._infer_max_score(response_content, module_id)
            
            return ModuleScore(
                module_id=module_id,
                score=score,
                max_score=max_score,
                justification=justification,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Failed to extract score for module {module_id}: {e}")
            return ModuleScore(
                module_id=module_id,
                score=0.0,
                max_score=max_score_hint or self._infer_max_score("", module_id),
                justification=f"Error extracting score: {str(e)}",
                success=False
            )
    
    def _extract_score_from_text(self, content: str) -> tuple[float, str]:
        """Extract score and justification from text content."""
        score = 0.0
        justification = "No clear score found in response"
        
        # Look for score patterns in the text
        score_patterns = [
            r'score[:\s]*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*/\s*\d+',
            r'awarded[:\s]*(\d+(?:\.\d+)?)',
            r'total[:\s]*(\d+(?:\.\d+)?)',
        ]
        
        for pattern in score_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                try:
                    score = float(matches[0])
                    break
                except ValueError:
                    continue
        
        # Extract justification (first 500 chars of content)
        if len(content) > 500:
            justification = content[:500] + "..."
        else:
            justification = content
            
        return score, justification
    
    def _infer_max_score(self, content: str, module_id: str) -> float:
        """Infer maximum score from content or module naming patterns."""
        # Look for patterns like "X points", "(X pts)", "X/Y"
        patterns = [
            r'(\d+)\s*points?',
            r'\((\d+)\s*pts?\)',
            r'\d+\s*/\s*(\d+)',
            r'out of (\d+)',
            r'maximum.*?(\d+)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                try:
                    return float(matches[-1])  # Take the last match
                except ValueError:
                    continue
        
        # Default fallbacks based on common module types
        if 'data_loading' in module_id or 'visualization' in module_id:
            return 5.0
        elif 'model' in module_id or 'optimization' in module_id:
            return 10.0
        elif 'analysis' in module_id:
            return 5.0
        elif 'documentation' in module_id:
            return 15.0
        
        return 10.0  # Default fallback
    
    def extract_student_scores(self, intermediate_dir: Path, task_name: str, 
                             module_max_scores: Optional[Dict[str, float]] = None) -> List[StudentScoreSummary]:
        """Extract scores for all students in a task."""
        student_summaries = []
        task_dir = intermediate_dir / task_name
        
        if not task_dir.exists():
            logger.warning(f"Task directory not found: {task_dir}")
            return student_summaries
        
        # Process each student directory
        for student_dir in task_dir.iterdir():
            if not student_dir.is_dir():
                continue
                
            student_id = student_dir.name
            logger.info(f"Processing scores for student: {student_id}")
            
            module_scores = []
            extraction_errors = []
            
            # Process each intermediate response file
            for response_file in student_dir.glob("*_intermediate.json"):
                try:
                    module_id = response_file.stem.replace('_intermediate', '')
                    
                    with open(response_file, 'r', encoding='utf-8') as f:
                        response_data = json.load(f)
                    
                    if not response_data.get('llm_call_success', False):
                        extraction_errors.append(f"LLM call failed for module {module_id}")
                        continue
                    
                    raw_content = response_data.get('raw_response_content', '')
                    max_score_hint = module_max_scores.get(module_id) if module_max_scores else None
                    
                    module_score = self.extract_score_from_response(
                        raw_content, module_id, max_score_hint
                    )
                    module_scores.append(module_score)
                    
                except Exception as e:
                    error_msg = f"Error processing {response_file.name}: {str(e)}"
                    extraction_errors.append(error_msg)
                    logger.error(error_msg)
            
            # Calculate totals
            total_score = sum(ms.score for ms in module_scores if ms.success)
            max_total_score = sum(ms.max_score for ms in module_scores if ms.success)
            percentage = (total_score / max_total_score * 100) if max_total_score > 0 else 0
            
            student_summary = StudentScoreSummary(
                student_id=student_id,
                task_name=task_name,
                total_score=total_score,
                max_total_score=max_total_score,
                percentage=percentage,
                module_scores=module_scores,
                extraction_errors=extraction_errors
            )
            
            student_summaries.append(student_summary)
        
        return student_summaries
    
    def save_scores_summary(self, student_summaries: List[StudentScoreSummary], 
                          output_path: Path) -> None:
        """Save the extracted scores to a JSON file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        summary_data = {
            "extraction_timestamp": str(Path().cwd()),
            "total_students": len(student_summaries),
            "students": [summary.model_dump() for summary in student_summaries]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved score summary to {output_path}")


def extract_scores_for_task(task_name: str, intermediate_dir: Path, 
                          results_dir: Path, module_max_scores: Optional[Dict[str, float]] = None) -> None:
    """Convenience function to extract scores for a specific task."""
    extractor = ScoreExtractor()
    
    student_summaries = extractor.extract_student_scores(
        intermediate_dir, task_name, module_max_scores
    )
    
    # Save to results directory
    output_path = results_dir / task_name / "scores_summary.json"
    extractor.save_scores_summary(student_summaries, output_path)
    
    logger.info(f"Extracted scores for {len(student_summaries)} students in task: {task_name}") 