from dataclasses import dataclass
from typing import Dict, List, Optional
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class TestSummary:
    passed: bool
    exit_code: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    success_rate: float

    @classmethod
    def from_dict(cls, data: Dict) -> 'TestSummary':
        summary = data.copy()
        summary['success_rate'] = (summary['passed_tests'] / summary['total_tests']) * 100
        return cls(**summary)
    
    def to_dict(self) -> Dict:
        return {
            'passed': self.passed,
            'exit_code': self.exit_code,
            'total_tests': self.total_tests,
            'passed_tests': self.passed_tests,
            'failed_tests': self.failed_tests,
            'success_rate': self.success_rate
        }


@dataclass
class TestDetails:
    test_cases: List[str]
    full_output: str

    @classmethod
    def from_dict(cls, data: Dict) -> 'TestDetails':
        return cls(**data)
    
    def to_dict(self) -> Dict:
        return {
            'test_cases': self.test_cases,
            'full_output': self.full_output
        }


@dataclass
class CodeQualityToolResult:
    name: str
    description: str
    output: str
    has_issues: bool
    warning: Optional[str]

    @classmethod
    def from_dict(cls, data: Dict) -> 'CodeQualityToolResult':
        return cls(**data)
    
    def to_dict(self) -> Dict:
        return {
            'name': self.name,
            'description': self.description,
            'output': self.output,
            'has_issues': self.has_issues,
            'warning': self.warning
        }


@dataclass
class CodeQualitySummary:
    has_quality_issues: bool
    tools_run: List[str]
    tool_results: Dict[str, CodeQualityToolResult]

    @classmethod
    def from_dict(cls, data: Dict) -> 'CodeQualitySummary':
        """Create CodeQualitySummary from dictionary data."""
        return cls(
            has_quality_issues=data['has_quality_issues'],
            tools_run=data['tools_run'],
            tool_results={}  # Will be set by ProblemResult
        )
    
    def to_dict(self) -> Dict:
        return {
            'has_quality_issues': self.has_quality_issues,
            'tools_run': self.tools_run,
            'tool_results': {
                tool: result.to_dict() 
                for tool, result in self.tool_results.items()
            }
        }


@dataclass
class ProblemResult:
    solution_path: str
    test_results: Dict
    code_quality: CodeQualitySummary

    @classmethod
    def from_dict(cls, data: Dict) -> 'ProblemResult':
        # Create code quality summary from the nested structure
        code_quality = CodeQualitySummary.from_dict(data['code_quality']['summary'])
        # Add tool results separately since they're at the same level as summary
        code_quality.tool_results = {
            tool: CodeQualityToolResult.from_dict(result)
            for tool, result in data['code_quality']['tool_results'].items()
        }
        
        # Convert solution path to absolute path
        solution_path = str(Path(data['solution_path']).resolve())
        
        return cls(
            solution_path=solution_path,
            test_results={
                'summary': TestSummary.from_dict(data['test_results']['summary']),
                'details': TestDetails.from_dict(data['test_results']['details'])
            },
            code_quality=code_quality
        )
    
    def to_dict(self) -> Dict:
        return {
            'solution_path': self.solution_path,
            'test_results': {
                'summary': self.test_results['summary'].to_dict(),
                'details': self.test_results['details'].to_dict()
            },
            'code_quality': {
                'summary': self.code_quality.to_dict()
            }
        }


@dataclass
class SubmissionMetadata:
    student_name: str
    student_id: str
    lab_number: str
    timestamp: str

    @classmethod
    def from_dict(cls, data: Dict) -> 'SubmissionMetadata':
        return cls(**data)
    
    def to_dict(self) -> Dict:
        return {
            'student_name': self.student_name,
            'student_id': self.student_id,
            'lab_number': self.lab_number,
            'timestamp': self.timestamp
        }


class TestResultAnalyzer:
    def __init__(self, results_json_path: str):
        """Initialize the analyzer with path to results JSON file."""
        self.results_json_path = results_json_path
        self.metadata = None
        self.problems = {}
        logger.info(f"Initializing TestResultAnalyzer with results file: {results_json_path}")
        self._load_results()

    def _load_results(self) -> None:
        """Load and parse the results JSON file."""
        try:
            logger.info("Loading results JSON file")
            with open(self.results_json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.info("Parsing metadata")
            self.metadata = SubmissionMetadata.from_dict(data['metadata'])
            logger.debug(f"Metadata loaded: {self.metadata.to_dict()}")
            
            logger.info("Parsing problem results")
            self.problems = {}
            for problem_id, problem_data in data['problems'].items():
                logger.debug(f"Processing problem {problem_id}")
                try:
                    self.problems[problem_id] = ProblemResult.from_dict(problem_data)
                    logger.debug(f"Successfully processed problem {problem_id}")
                except Exception as e:
                    logger.error(f"Error processing problem {problem_id}: {str(e)}")
                    logger.exception("Detailed error traceback:")
                    raise
            
            logger.info(f"Successfully loaded {len(self.problems)} problems")
            
        except UnicodeDecodeError as e:
            logger.error(f"Error reading file (encoding issue): {str(e)}")
            logger.info("Attempting to read with different encoding...")
            try:
                # Try reading with a more permissive encoding
                with open(self.results_json_path, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                logger.info("Successfully read file with utf-8-sig encoding")
                # Continue with the same processing...
                self.metadata = SubmissionMetadata.from_dict(data['metadata'])
                self.problems = {}
                for problem_id, problem_data in data['problems'].items():
                    self.problems[problem_id] = ProblemResult.from_dict(problem_data)
                logger.info(f"Successfully loaded {len(self.problems)} problems")
            except Exception as e2:
                logger.error(f"Error loading results with alternative encoding: {str(e2)}")
                logger.exception("Detailed error traceback:")
                raise
        except Exception as e:
            logger.error(f"Error loading results: {str(e)}")
            logger.exception("Detailed error traceback:")
            raise

    def get_problem_analysis(self, problem_id: str) -> Dict:
        """Get detailed analysis for a specific problem."""
        logger.info(f"Getting analysis for problem {problem_id}")
        
        if problem_id not in self.problems:
            error_msg = f"Problem {problem_id} not found in results"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        problem = self.problems[problem_id]
        logger.debug(f"Problem data type: {type(problem)}")
        
        try:
            analysis = {
                'success_rate': problem.test_results['summary'].success_rate,
                'passed_all_tests': problem.test_results['summary'].passed,
                'test_cases': problem.test_results['details'].test_cases,
                'has_quality_issues': problem.code_quality.has_quality_issues,
                'quality_tools': {
                    tool: result.output
                    for tool, result in problem.code_quality.tool_results.items()
                    if result.has_issues
                }
            }
            logger.debug(f"Analysis result: {analysis}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing problem {problem_id}: {str(e)}")
            logger.exception("Detailed error traceback:")
            raise

    def get_overall_success_rate(self) -> float:
        """Calculate the overall success rate across all problems."""
        logger.info("Calculating overall success rate")
        total_passed = 0
        total_tests = 0
        
        for problem in self.problems.values():
            summary = problem.test_results['summary']
            total_passed += summary.passed_tests
            total_tests += summary.total_tests
            
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0.0
        logger.debug(f"Overall success rate: {success_rate}%")
        return success_rate

    def get_code_quality_summary(self) -> Dict[str, int]:
        """Get a summary of code quality issues across all problems."""
        logger.info("Getting code quality summary")
        issues_count = {'total': 0}
        
        for problem in self.problems.values():
            quality = problem.code_quality
            if quality.has_quality_issues:
                issues_count['total'] += 1
                for tool, result in quality.tool_results.items():
                    if result.has_issues:
                        issues_count[tool] = issues_count.get(tool, 0) + 1
        
        logger.debug(f"Code quality summary: {issues_count}")
        return issues_count

    def get_submission_summary(self) -> Dict:
        """Get a high-level summary of the entire submission."""
        logger.info("Getting submission summary")
        try:
            summary = {
                'student': {
                    'name': self.metadata.student_name,
                    'id': self.metadata.student_id,
                    'lab': self.metadata.lab_number,
                    'submission_time': self.metadata.timestamp
                },
                'overall_success_rate': self.get_overall_success_rate(),
                'problems_attempted': len(self.problems),
                'problems_with_quality_issues': len([
                    p for p in self.problems.values()
                    if p.code_quality.has_quality_issues
                ]),
                'problems_passing_all_tests': len([
                    p for p in self.problems.values()
                    if p.test_results['summary'].passed
                ])
            }
            logger.debug(f"Submission summary: {summary}")
            return summary
            
        except Exception as e:
            logger.error("Error generating submission summary")
            logger.exception("Detailed error traceback:")
            raise
