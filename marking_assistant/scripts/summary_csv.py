#!/usr/bin/env python3
"""
Summary CSV Generator Script

This script creates comprehensive CSV reports from marking results and feedback data.
It gathers information from:
- results/{task_name}/scores_summary.json (extracted scores)
- feedback/{task_name}/*.md (feedback reports)
- results/{task_name}/*_test_results.json (test results)
- results/{task_name}/*_quality_results.json (quality metrics)

Usage:
    python scripts/summary_csv.py --task-name "TASK_NAME" [options]
"""

import argparse
import json
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any
import re
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class SummaryCSVGenerator:
    """Generates comprehensive CSV summaries from marking pipeline results."""
    
    def __init__(self, results_dir: Path, feedback_dir: Path):
        self.results_dir = results_dir
        self.feedback_dir = feedback_dir
    
    def extract_student_name_from_feedback(self, feedback_path: Path) -> Optional[str]:
        """Extract student name from feedback file name or content."""
        try:
            # Try to extract from filename first
            filename = feedback_path.stem
            # Pattern: Name_Name_zID_task_feedback
            parts = filename.split('_')
            if len(parts) >= 3:
                # Find the student ID (starts with 'z')
                student_id_idx = None
                for i, part in enumerate(parts):
                    if part.startswith('z') and part[1:].isdigit():
                        student_id_idx = i
                        break
                
                if student_id_idx and student_id_idx > 0:
                    # Name parts are before the student ID
                    name_parts = parts[:student_id_idx]
                    return ' '.join(name_parts).replace('_', ' ')
            
            # Fallback: try to extract from file content
            content = feedback_path.read_text(encoding='utf-8')
            match = re.search(r'Student:\s*([^(]+)', content)
            if match:
                return match.group(1).strip()
                
        except Exception as e:
            logger.warning(f"Could not extract student name from {feedback_path}: {e}")
        
        return None
    
    def load_scores_data(self, task_name: str) -> Dict[str, Any]:
        """Load the scores summary JSON file."""
        scores_file = self.results_dir / task_name / "scores_summary.json"
        
        if not scores_file.exists():
            logger.warning(f"Scores summary file not found: {scores_file}")
            return {"students": []}
        
        try:
            with open(scores_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load scores data: {e}")
            return {"students": []}
    
    def load_test_results(self, task_name: str) -> Dict[str, Dict]:
        """Load test results for all students."""
        test_results = {}
        task_results_dir = self.results_dir / task_name
        
        if not task_results_dir.exists():
            return test_results
        
        for test_file in task_results_dir.glob("*_test_results.json"):
            try:
                with open(test_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Extract student ID from filename
                    student_id = self._extract_student_id_from_filename(test_file.name)
                    if student_id:
                        test_results[student_id] = data
            except Exception as e:
                logger.warning(f"Failed to load test results from {test_file}: {e}")
        
        return test_results
    
    def load_quality_results(self, task_name: str) -> Dict[str, Dict]:
        """Load quality results for all students."""
        quality_results = {}
        task_results_dir = self.results_dir / task_name
        
        if not task_results_dir.exists():
            return quality_results
        
        for quality_file in task_results_dir.glob("*_quality_results.json"):
            try:
                with open(quality_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    student_id = self._extract_student_id_from_filename(quality_file.name)
                    if student_id:
                        quality_results[student_id] = data
            except Exception as e:
                logger.warning(f"Failed to load quality results from {quality_file}: {e}")
        
        return quality_results
    
    def load_feedback_data(self, task_name: str) -> Dict[str, Dict]:
        """Load feedback data for all students."""
        feedback_data = {}
        task_feedback_dir = self.feedback_dir / task_name
        
        if not task_feedback_dir.exists():
            logger.warning(f"Feedback directory not found: {task_feedback_dir}")
            return feedback_data
        
        for feedback_file in task_feedback_dir.glob("*.md"):
            try:
                student_id = self._extract_student_id_from_filename(feedback_file.name)
                if student_id:
                    content = feedback_file.read_text(encoding='utf-8')
                    student_name = self.extract_student_name_from_feedback(feedback_file)
                    
                    feedback_data[student_id] = {
                        'student_name': student_name,
                        'feedback_content': content,
                        'feedback_length': len(content),
                        'feedback_file': str(feedback_file)
                    }
            except Exception as e:
                logger.warning(f"Failed to load feedback from {feedback_file}: {e}")
        
        return feedback_data
    
    def _extract_student_id_from_filename(self, filename: str) -> Optional[str]:
        """Extract student ID (zXXXXXXX) from filename."""
        match = re.search(r'(z\d+)', filename)
        return match.group(1) if match else None
    
    def calculate_test_summary(self, test_data: Dict) -> Dict[str, Any]:
        """Calculate summary statistics from test results."""
        if not test_data:
            return {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'test_pass_rate': 0.0,
                'test_score': 0.0
            }
        
        total_tests = 0
        passed_tests = 0
        
        # Handle different test result structures
        if 'test_results' in test_data:
            results = test_data['test_results']
            if isinstance(results, list):
                total_tests = len(results)
                passed_tests = sum(1 for r in results if r.get('passed', False))
            elif isinstance(results, dict):
                total_tests = len(results)
                passed_tests = sum(1 for r in results.values() if r.get('passed', False))
        
        pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        return {
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': total_tests - passed_tests,
            'test_pass_rate': round(pass_rate, 2),
            'test_score': round(pass_rate, 2)  # Simple scoring based on pass rate
        }
    
    def calculate_quality_summary(self, quality_data: Dict) -> Dict[str, Any]:
        """Calculate summary from quality metrics."""
        if not quality_data:
            return {
                'code_quality_score': 0.0,
                'complexity_score': 0.0,
                'documentation_score': 0.0,
                'style_issues': 0
            }
        
        # Extract relevant quality metrics
        summary = {
            'code_quality_score': quality_data.get('overall_score', 0.0),
            'complexity_score': quality_data.get('complexity_score', 0.0),
            'documentation_score': quality_data.get('documentation_score', 0.0),
            'style_issues': quality_data.get('style_issues_count', 0)
        }
        
        return summary
    
    def generate_summary_csv(self, task_name: str, output_path: Optional[Path] = None) -> Path:
        """Generate the main summary CSV file."""
        logger.info(f"Generating summary CSV for task: {task_name}")
        
        # Load all data sources
        scores_data = self.load_scores_data(task_name)
        test_results = self.load_test_results(task_name)
        quality_results = self.load_quality_results(task_name)
        feedback_data = self.load_feedback_data(task_name)
        
        # Prepare data for CSV
        csv_rows = []
        
        for student_data in scores_data.get('students', []):
            student_id = student_data['student_id']
            
            # Basic student info
            row = {
                'student_id': student_id,
                'student_name': student_data.get('student_name') or 
                              feedback_data.get(student_id, {}).get('student_name', 'Unknown'),
                'task_name': task_name,
                'submission_date': datetime.now().strftime('%Y-%m-%d'),
            }
            
            # Scoring information
            row.update({
                'total_score': student_data.get('total_score', 0),
                'max_total_score': student_data.get('max_total_score', 0),
                'percentage_score': student_data.get('percentage', 0),
                'module_count': len(student_data.get('module_scores', [])),
                'extraction_errors': len(student_data.get('extraction_errors', []))
            })
            
            # Test results summary
            test_summary = self.calculate_test_summary(test_results.get(student_id, {}))
            row.update({f'test_{k}': v for k, v in test_summary.items()})
            
            # Quality metrics summary
            quality_summary = self.calculate_quality_summary(quality_results.get(student_id, {}))
            row.update({f'quality_{k}': v for k, v in quality_summary.items()})
            
            # Feedback information
            feedback_info = feedback_data.get(student_id, {})
            row.update({
                'has_feedback': bool(feedback_info),
                'feedback_length': feedback_info.get('feedback_length', 0),
                'feedback_file': feedback_info.get('feedback_file', '')
            })
            
            csv_rows.append(row)
        
        # Create DataFrame and save
        df = pd.DataFrame(csv_rows)
        
        if output_path is None:
            output_path = Path(f"summary_{task_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        
        df.to_csv(output_path, index=False)
        logger.info(f"Summary CSV saved to: {output_path}")
        
        return output_path
    
    def generate_detailed_scores_csv(self, task_name: str, output_path: Optional[Path] = None) -> Path:
        """Generate a detailed CSV with individual module scores."""
        logger.info(f"Generating detailed scores CSV for task: {task_name}")
        
        scores_data = self.load_scores_data(task_name)
        feedback_data = self.load_feedback_data(task_name)
        
        csv_rows = []
        
        for student_data in scores_data.get('students', []):
            student_id = student_data['student_id']
            student_name = student_data.get('student_name') or \
                          feedback_data.get(student_id, {}).get('student_name', 'Unknown')
            
            for module_score in student_data.get('module_scores', []):
                row = {
                    'student_id': student_id,
                    'student_name': student_name,
                    'task_name': task_name,
                    'module_id': module_score['module_id'],
                    'module_score': module_score['score'],
                    'module_max_score': module_score['max_score'],
                    'module_percentage': (module_score['score'] / module_score['max_score'] * 100) 
                                       if module_score['max_score'] > 0 else 0,
                    'module_success': module_score['success'],
                    'justification': module_score['justification'][:200] + '...' 
                                   if len(module_score['justification']) > 200 
                                   else module_score['justification']
                }
                csv_rows.append(row)
        
        df = pd.DataFrame(csv_rows)
        
        if output_path is None:
            output_path = Path(f"detailed_scores_{task_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        
        df.to_csv(output_path, index=False)
        logger.info(f"Detailed scores CSV saved to: {output_path}")
        
        return output_path
    
    def generate_all_reports(self, task_name: str, output_dir: Optional[Path] = None) -> Dict[str, Path]:
        """Generate all CSV reports for a task."""
        if output_dir is None:
            output_dir = Path("reports")
        
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_task_name = task_name.replace(' ', '_').replace('(', '').replace(')', '')
        
        reports = {}
        
        # Generate summary CSV
        summary_path = output_dir / f"summary_{safe_task_name}_{timestamp}.csv"
        reports['summary'] = self.generate_summary_csv(task_name, summary_path)
        
        # Generate detailed scores CSV
        detailed_path = output_dir / f"detailed_scores_{safe_task_name}_{timestamp}.csv"
        reports['detailed_scores'] = self.generate_detailed_scores_csv(task_name, detailed_path)
        
        return reports


def main():
    parser = argparse.ArgumentParser(description="Generate CSV summaries from marking results")
    parser.add_argument("--task-name", type=str, required=True, 
                       help="Name of the task to generate summary for")
    parser.add_argument("--results-dir", type=Path, default=Path("results"),
                       help="Directory containing results data")
    parser.add_argument("--feedback-dir", type=Path, default=Path("feedback"),
                       help="Directory containing feedback files")
    parser.add_argument("--output-dir", type=Path, default=Path("reports"),
                       help="Directory to save CSV reports")
    parser.add_argument("--summary-only", action="store_true",
                       help="Generate only the summary CSV (not detailed scores)")
    parser.add_argument("--detailed-only", action="store_true",
                       help="Generate only the detailed scores CSV")
    
    args = parser.parse_args()
    
    # Validate directories
    if not args.results_dir.exists():
        logger.error(f"Results directory not found: {args.results_dir}")
        return 1
    
    if not args.feedback_dir.exists():
        logger.warning(f"Feedback directory not found: {args.feedback_dir}")
    
    # Create output directory
    args.output_dir.mkdir(exist_ok=True)
    
    # Initialize generator
    generator = SummaryCSVGenerator(args.results_dir, args.feedback_dir)
    
    try:
        if args.summary_only:
            summary_path = generator.generate_summary_csv(args.task_name)
            print(f"Summary CSV generated: {summary_path}")
        elif args.detailed_only:
            detailed_path = generator.generate_detailed_scores_csv(args.task_name)
            print(f"Detailed scores CSV generated: {detailed_path}")
        else:
            reports = generator.generate_all_reports(args.task_name, args.output_dir)
            print("Generated reports:")
            for report_type, path in reports.items():
                print(f"  {report_type}: {path}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to generate CSV reports: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit(main()) 