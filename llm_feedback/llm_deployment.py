from typing import Dict, List, Optional, Union
import json
import ollama
from dataclasses import dataclass
import logging
import os
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import yaml

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
class LLMResponse:
    """Structured response from LLM."""
    content: str
    raw_response: Dict
    success: bool
    error: Optional[str] = None


class LLMDeployment:
    """Interface for LLM interactions using Ollama and OpenAI."""
    
    def __init__(self, model_name: str = "qwq"):
        """Initialize LLM deployment.
        
        Args:
            model_name: Name of the model to use (default: "qwq")
                      Can be an Ollama model or "openai-gpt-4o" for OpenAI
        """
        self.model_name = model_name
        self.use_openai = model_name.startswith("openai-")
        
        if self.use_openai:
            if not os.getenv("OPENAI_API_KEY"):
                raise RuntimeError("OpenAI API key not found in environment variables")
            try:
                # Initialize OpenAI client with default configuration
                self.client = OpenAI()
                logger.info(f"Using OpenAI model: {model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {str(e)}")
                raise RuntimeError(f"Failed to initialize OpenAI client: {str(e)}")
        else:
            self._verify_model()

    def _verify_model(self) -> None:
        """Verify that the specified model is available in Ollama."""
        try:
            ollama.chat(model=self.model_name, messages=[{"role": "user", "content": "test"}])
            logger.info(f"Successfully verified model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to verify model {self.model_name}: {str(e)}")
            raise RuntimeError(f"Model {self.model_name} is not available in Ollama")

    def _safe_chat(self, messages: List[Dict[str, str]], system_prompt: Optional[str] = None) -> LLMResponse:
        """Safely execute chat with error handling.
        
        Args:
            messages: List of message dictionaries with role and content
            system_prompt: Optional system prompt to set context
            
        Returns:
            LLMResponse object containing the response and status
        """
        try:
            if system_prompt:
                messages.insert(0, {"role": "system", "content": system_prompt})
            
            if self.use_openai:
                # Convert messages to OpenAI format
                openai_messages = [{"role": msg["role"], "content": msg["content"]} for msg in messages]
                response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=openai_messages
                )
                return LLMResponse(
                    content=response.choices[0].message.content,
                    raw_response=response.to_dict(),
                    success=True
                )
            else:
                response = ollama.chat(model=self.model_name, messages=messages)
                return LLMResponse(
                    content=response["message"]["content"],
                    raw_response=response,
                    success=True
                )
        except Exception as e:
            logger.error(f"Error in LLM chat: {str(e)}")
            return LLMResponse(
                content="",
                raw_response={},
                success=False,
                error=str(e)
            )

    def analyze_test_results(self, test_results: Dict, rubric_criteria: Optional[Dict] = None) -> LLMResponse:
        """Analyze test results and generate insights.
        
        Args:
            test_results: Dictionary containing test results
            rubric_criteria: Optional rubric criteria for context
            
        Returns:
            LLMResponse with analysis
        """
        content = json.dumps(test_results, indent=2)
        if rubric_criteria:
            content += "\n\nRubric Criteria:\n" + json.dumps(rubric_criteria, indent=2)
            
        messages = [{"role": "user", "content": content}]
        return self._safe_chat(messages, PROMPTS['test_analysis']['system_prompt'])

    def generate_feedback(self, 
                        test_analysis: Dict, 
                        code_quality: Dict,
                        rubric_evaluation: Optional[Dict] = None) -> LLMResponse:
        """Generate comprehensive feedback based on test analysis and code quality.
        
        Args:
            test_analysis: Dictionary containing test result analysis
            code_quality: Dictionary containing code quality metrics
            rubric_evaluation: Optional rubric evaluation results
            
        Returns:
            LLMResponse with formatted feedback
        """
        content = {
            "test_analysis": test_analysis,
            "code_quality": code_quality,
            "rubric_evaluation": rubric_evaluation
        }
        
        messages = [{"role": "user", "content": json.dumps(content, indent=2)}]
        return self._safe_chat(messages, PROMPTS['feedback_generation']['system_prompt'])

    def calculate_score(self, 
                       test_results: Dict,
                       code_quality: Dict,
                       rubric: Dict,
                       max_score: float) -> LLMResponse:
        """Calculate score based on test results, code quality, and rubric.
        
        Args:
            test_results: Dictionary containing test results
            code_quality: Dictionary containing code quality metrics
            rubric: Dictionary containing rubric criteria and weights
            max_score: Maximum possible score
            
        Returns:
            LLMResponse with calculated score and justification
        """
        content = {
            "test_results": test_results,
            "code_quality": code_quality,
            "rubric": rubric,
            "max_score": max_score
        }
        
        messages = [{"role": "user", "content": json.dumps(content, indent=2)}]
        return self._safe_chat(messages, PROMPTS['score_calculation']['system_prompt'])

    def analyze_code_quality(self, quality_report: Dict) -> LLMResponse:
        """Analyze code quality report and provide insights.
        
        Args:
            quality_report: Dictionary containing code quality metrics
            
        Returns:
            LLMResponse with analysis of code quality
        """
        messages = [{"role": "user", "content": json.dumps(quality_report, indent=2)}]
        return self._safe_chat(messages, PROMPTS['code_quality']['system_prompt'])

    def evaluate_rubric_criteria(self, 
                               submission_data: Dict,
                               rubric: Dict) -> LLMResponse:
        """Evaluate submission against rubric criteria.
        
        Args:
            submission_data: Dictionary containing submission details
            rubric: Dictionary containing rubric criteria
            
        Returns:
            LLMResponse with evaluation against each rubric criterion
        """
        system_prompt = """You are an expert programming instructor evaluating a submission against rubric criteria.
        Provide specific evidence and justification for how each criterion is met or not met."""
        
        content = {
            "submission": submission_data,
            "rubric": rubric
        }
        
        messages = [{"role": "user", "content": json.dumps(content, indent=2)}]
        return self._safe_chat(messages, system_prompt)

    def custom_analysis(self, 
                       data: Union[Dict, str],
                       system_prompt: str,
                       user_prompt: Optional[str] = None) -> LLMResponse:
        """Perform custom analysis with specified prompts.
        
        Args:
            data: Data to analyze (dictionary or string)
            system_prompt: System prompt for setting context
            user_prompt: Optional additional user prompt
            
        Returns:
            LLMResponse with analysis
        """
        content = data if isinstance(data, str) else json.dumps(data, indent=2)
        if user_prompt:
            content = f"{user_prompt}\n\n{content}"
            
        messages = [{"role": "user", "content": content}]
        return self._safe_chat(messages, system_prompt)
