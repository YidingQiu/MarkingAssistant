import logging
import json
import argparse
from pathlib import Path
from typing import Dict, Any, List, Type

from ..assignments.loaders import MoodleLoader
from ..runners.test_runner import TestRunner
from ..feedback.llm_provider import LLMProvider
from ..feedback.output_models import OUTPUT_MODEL_REGISTRY, BaseFeedbackOutput
from .data_collector import DataCollector
from ..analysis.score_extractor import extract_scores_for_task
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class MarkingPipeline:
    """Orchestrates the entire marking process for a given task based on a modular configuration."""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.task_name = config.get('task_name', 'unknown_task')
        
        # Initialize components based on config
        self.loader = MoodleLoader(config.get('submissions_dir', 'submissions'))
        self.test_runner = TestRunner(
            test_cases_dir=config.get('test_cases_dir', f'rubric/test_cases/{self.task_name}'),
            results_dir=config.get('results_dir', 'results'),
            task_name=self.task_name
        )
        self.llm_provider = LLMProvider(
            model_name=config.get('model', 'openai-gpt-4o'),
            temperature=config.get('temperature', 0.1)
        )
        self.save_intermediate_responses = config.get('save_intermediate_responses', True)
        self.intermediate_dir = Path(config.get('results_dir', 'results')) / 'intermediate_responses'
        self.results_dir = Path(config.get('results_dir', 'results'))
        
        # Extract module max scores from config for score extraction
        self.module_max_scores = self._extract_module_max_scores()

    def _extract_module_max_scores(self) -> Dict[str, float]:
        """Extract maximum scores for each module from the configuration."""
        module_max_scores = {}
        modules_config = self.config.get('modules', [])
        
        for module_cfg in modules_config:
            module_id = module_cfg.get('module_id')
            if not module_id:
                continue
                
            # Try to extract max score from user prompt template
            user_prompt = module_cfg.get('user_prompt_template', '')
            
            # Look for patterns like "(X points)", "X points total", etc.
            import re
            patterns = [
                r'\((\d+)\s*points?\)',
                r'(\d+)\s*points?\s*total',
                r'Assessment Focus:.*?\((\d+)\s*points?\)',
                r'(\d+)\s*points?\)',
            ]
            
            max_score = None
            for pattern in patterns:
                matches = re.findall(pattern, user_prompt, re.IGNORECASE)
                if matches:
                    try:
                        max_score = float(matches[0])
                        break
                    except ValueError:
                        continue
            
            if max_score is not None:
                module_max_scores[module_id] = max_score
            else:
                # Default fallbacks based on module naming
                if 'data_loading' in module_id or 'visualization' in module_id:
                    module_max_scores[module_id] = 5.0
                elif 'model' in module_id or 'optimization' in module_id:
                    module_max_scores[module_id] = 10.0
                elif 'analysis' in module_id:
                    module_max_scores[module_id] = 5.0
                elif 'documentation' in module_id:
                    module_max_scores[module_id] = 15.0
                else:
                    module_max_scores[module_id] = 10.0
        
        return module_max_scores

    def run(self):
        """Executes the marking pipeline for the configured task."""
        logger.info(f"Starting modular marking pipeline for task: {self.task_name}")

        submissions = self.loader.get_submissions_for_task(self.task_name)
        if not submissions:
            logger.warning("No submissions found. Exiting pipeline.")
            return

        for submission in submissions:
            logger.info(f"Processing submission for student: {submission.student.name} ({submission.student.id})")
            
            try:
                # 1. Run tests and quality checks to get raw results
                test_results, quality_results = self.test_runner.run_tests_for_submission(submission)
                
                # 2. Set up the data collector with all available results
                data_collector = DataCollector(submission, test_results, quality_results)
                
                # 3. Execute modules defined in config
                module_outputs = self._execute_modules(data_collector)
                
                # 4. Assemble the final report
                final_report = self._assemble_report(module_outputs, submission.student)
                
                # 5. Save the report
                self._save_report(final_report, submission.student)

            except Exception as e:
                logger.error(f"Failed to process submission for {submission.student.name}: {e}", exc_info=True)

        # 6. Extract scores after all submissions are processed
        logger.info("Extracting scores from intermediate responses...")
        try:
            extract_scores_for_task(
                self.task_name, 
                self.intermediate_dir, 
                self.results_dir,
                self.module_max_scores
            )
        except Exception as e:
            logger.error(f"Failed to extract scores: {e}", exc_info=True)

        logger.info(f"Modular marking pipeline for task {self.task_name} finished.")

    def _execute_modules(self, data_collector: DataCollector) -> Dict[str, Any]:
        """Iterates through and executes all modules defined in the task config."""
        module_outputs = {}
        modules_config = self.config.get('modules', [])
        
        if not modules_config:
            logger.warning(f"No modules defined for task '{self.task_name}'. No LLM feedback will be generated.")
            return module_outputs

        for module_cfg in modules_config:
            module_id = module_cfg.get('module_id')
            if not module_id:
                logger.warning("Skipping module with no ID.")
                continue
            
            logger.info(f"Executing module: {module_id}")
            
            # Gather data for this module
            required_data = module_cfg.get('required_data', {})
            prompt_vars = data_collector.gather_data_for_module(required_data, module_outputs)
            
            system_prompt = module_cfg.get('system_prompt_template', "").format(**prompt_vars)
            user_prompt = module_cfg.get('user_prompt_template', "").format(**prompt_vars)
            
            # Get the Pydantic model for structured output
            output_model_name = module_cfg.get('output_model_name', 'TextFeedback')
            output_model_class: Type[BaseFeedbackOutput] = OUTPUT_MODEL_REGISTRY.get(output_model_name, BaseFeedbackOutput)

            # Enhance prompt with JSON schema instruction
            json_schema = output_model_class.model_json_schema()
            system_prompt_with_json = (
                f"{system_prompt}\n\n"
                f"Your response MUST be a single, valid JSON object that conforms to the following JSON schema. "
                f"Do not include any text before or after the JSON object.\n"
                f"JSON Schema:\n{json.dumps(json_schema, indent=2)}"
            )

            # Call LLM
            response = self.llm_provider.generate(system_prompt_with_json, user_prompt)
            
            if self.save_intermediate_responses:
                self._save_intermediate_response(
                    student_id=data_collector.submission.student.id,
                    module_id=module_id,
                    system_prompt=system_prompt_with_json,
                    user_prompt=user_prompt,
                    raw_response=response
                )

            if response.success:
                try:
                    # Clean the output if necessary 
                    cleaned_text = response.content.strip()
                    if cleaned_text.startswith("```json"):
                        cleaned_text = cleaned_text[len("```json"):].strip()
                    if cleaned_text.endswith("```"):
                        cleaned_text = cleaned_text[:-len("```")].strip()
                    
                    parsed_output = output_model_class.model_validate_json(cleaned_text)
                    module_outputs[module_id] = parsed_output
                except (json.JSONDecodeError, ValidationError) as e:
                    logger.error(f"Failed to parse LLM output for module {module_id} as {output_model_name}: {e}")
                    logger.debug(f"Raw LLM output:\n{response.content}")
                    module_outputs[module_id] = f"Error: Could not parse LLM response. Raw output: {response.content}"
            else:
                module_outputs[module_id] = f"Error generating feedback for this module: {response.error}"
        
        return module_outputs

    def _save_intermediate_response(self, student_id: str, module_id: str, system_prompt: str, user_prompt: str, raw_response):
        """Saves the prompts and raw response for a single module execution."""
        try:
            student_dir = self.intermediate_dir / self.task_name / str(student_id)
            student_dir.mkdir(parents=True, exist_ok=True)
            
            output_path = student_dir / f"{module_id}_intermediate.json"
            
            data_to_save = {
                "module_id": module_id,
                "student_id": str(student_id),
                "task_name": self.task_name,
                "llm_call_success": raw_response.success,
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "raw_response_content": raw_response.content,
                "error_message": raw_response.error,
            }
            
            output_path.write_text(json.dumps(data_to_save, indent=2), encoding='utf-8')
            logger.debug(f"Saved intermediate response for module {module_id} to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to save intermediate response for module {module_id} for student {student_id}: {e}")

    def _assemble_report(self, module_outputs: Dict[str, Any], student) -> str:
        """Assembles the final report from module outputs based on a template."""
        report_structure = self.config.get('report_structure', {})
        header = report_structure.get('header', "").format(user_name=student.name, user_id=student.id, task_name=self.task_name)
        footer = report_structure.get('footer', "")
        
        sections = []
        for section_cfg in report_structure.get('sections', []):
            module_id = section_cfg.get('module_id')
            title = section_cfg.get('title', f"### {module_id}\n")
            
            content_obj = module_outputs.get(module_id)
            content = ""
            if isinstance(content_obj, BaseFeedbackOutput):
                # Convert pydantic model to a string for the report.
                # This could be more sophisticated, e.g., calling a .to_markdown() method.
                if hasattr(content_obj, 'feedback_text'):
                    content = content_obj.feedback_text
                else:
                    content = content_obj.model_dump_json(indent=2)
            elif isinstance(content_obj, str):
                content = content_obj # It was an error message
            else:
                content = f"Content for module '{module_id}' not generated or in unknown format."

            sections.append(f"{title}\n{content}")
            
        return f"{header}\n\n" + "\n\n".join(sections) + f"\n\n{footer}"

    def _save_report(self, report_content: str, student):
        """Saves the final report to a file."""
        feedback_dir = Path(self.config.get('feedback_dir', 'feedback')) / self.task_name
        feedback_dir.mkdir(parents=True, exist_ok=True)
        
        safe_name = student.name.replace(' ', '_')
        report_filename = f"{safe_name}_{student.id}_{self.task_name}_feedback.md"
        report_path = feedback_dir / report_filename
        
        try:
            report_path.write_text(report_content, encoding='utf-8')
            logger.info(f"Successfully saved final report to {report_path}")
        except Exception as e:
            logger.error(f"Failed to save final report to {report_path}: {e}")

# Example of how this might be run from a script
def main():
    # This would come from argparse or a main script
    parser = argparse.ArgumentParser(description="Run the marking pipeline for a specific task.")
    parser.add_argument("--task-name", type=str, required=True, help="The name of the task to process.")
    parser.add_argument("--submissions-dir", type=str, default="submissions", help="Directory containing submissions.")
    parser.add_argument("--results-dir", type=str, default="results", help="Directory to save test results.")
    parser.add_argument("--test-cases-dir", type=str, default="rubric/test_cases", help="Directory with test cases.")
    parser.add_argument("--model", type=str, default="openai-gpt-4o", help="LLM model to use for feedback.")
    parser.add_argument("--feedback-dir", type=str, default="feedback", help="Directory to save feedback reports.")
    args = parser.parse_args()

    pipeline_config = {
        'task_name': args.task_name,
        'submissions_dir': args.submissions_dir,
        'results_dir': args.results_dir,
        'test_cases_dir': args.test_cases_dir,
        'model': args.model,
        'feedback_dir': args.feedback_dir,
    }
    
    pipeline = MarkingPipeline(pipeline_config)
    pipeline.run()

if __name__ == '__main__':
    # This is for demonstration. A real entrypoint would be in the /scripts folder.
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    main() 