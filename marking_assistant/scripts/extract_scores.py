#!/usr/bin/env python3
"""
Score Extraction Script

This script extracts scores from existing intermediate response files using PydanticAI.
It can be run independently of the main marking pipeline to process already generated
intermediate responses.

Usage:
    python scripts/extract_scores.py --task-name "TASK_NAME" [options]
"""

import argparse
import logging
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from marking_assistant.analysis.score_extractor import extract_scores_for_task

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_module_max_scores_from_config(config_path: Path) -> dict:
    """Load module max scores from the task configuration file."""
    import yaml
    import re
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        module_max_scores = {}
        modules_config = config.get('modules', [])
        
        for module_cfg in modules_config:
            module_id = module_cfg.get('module_id')
            if not module_id:
                continue
                
            # Try to extract max score from user prompt template
            user_prompt = module_cfg.get('user_prompt_template', '')
            
            # Look for patterns like "(X points)", "X points total", etc.
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
        
        logger.info(f"Loaded max scores for {len(module_max_scores)} modules from config")
        return module_max_scores
        
    except Exception as e:
        logger.error(f"Failed to load config from {config_path}: {e}")
        return {}


def main():
    parser = argparse.ArgumentParser(description="Extract scores from intermediate response files")
    parser.add_argument("--task-name", type=str, required=True,
                       help="Name of the task to extract scores for")
    parser.add_argument("--intermediate-dir", type=Path, default=Path("results/intermediate_responses"),
                       help="Directory containing intermediate response files")
    parser.add_argument("--results-dir", type=Path, default=Path("results"),
                       help="Directory to save extracted scores")
    parser.add_argument("--config-file", type=Path,
                       help="Path to task configuration file (to extract max scores)")
    parser.add_argument("--model", type=str, default="openai:gpt-4o-mini",
                       help="Model to use for score extraction")
    
    args = parser.parse_args()
    
    # Validate directories
    if not args.intermediate_dir.exists():
        logger.error(f"Intermediate responses directory not found: {args.intermediate_dir}")
        return 1
    
    task_intermediate_dir = args.intermediate_dir / args.task_name
    if not task_intermediate_dir.exists():
        logger.error(f"Task intermediate directory not found: {task_intermediate_dir}")
        return 1
    
    # Load module max scores from config if provided
    module_max_scores = None
    if args.config_file and args.config_file.exists():
        module_max_scores = load_module_max_scores_from_config(args.config_file)
    
    try:
        logger.info(f"Extracting scores for task: {args.task_name}")
        extract_scores_for_task(
            args.task_name,
            args.intermediate_dir,
            args.results_dir,
            module_max_scores
        )
        
        output_file = args.results_dir / args.task_name / "scores_summary.json"
        logger.info(f"Score extraction completed. Results saved to: {output_file}")
        return 0
        
    except Exception as e:
        logger.error(f"Failed to extract scores: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main()) 