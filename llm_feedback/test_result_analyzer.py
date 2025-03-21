from dataclasses import dataclass
from typing import Dict, List, Optional
import json


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
        
        return cls(
            solution_path=data['solution_path'],
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
        self._load_results()

    def _load_results(self) -> None:
        """Load and parse the results JSON file."""
        with open(self.results_json_path, 'r') as f:
            data = json.load(f)
            
        self.metadata = SubmissionMetadata.from_dict(data['metadata'])
        self.problems = {
            problem_id: ProblemResult.from_dict(problem_data)
            for problem_id, problem_data in data['problems'].items()
        }

    def get_overall_success_rate(self) -> float:
        """Calculate the overall success rate across all problems."""
        total_passed = 0
        total_tests = 0
        
        for problem in self.problems.values():
            summary = problem.test_results['summary']
            total_passed += summary.passed_tests
            total_tests += summary.total_tests
            
        return (total_passed / total_tests * 100) if total_tests > 0 else 0.0

    def get_code_quality_summary(self) -> Dict[str, int]:
        """Get a summary of code quality issues across all problems."""
        issues_count = {'total': 0}
        
        for problem in self.problems.values():
            quality = problem.code_quality
            if quality.has_quality_issues:
                issues_count['total'] += 1
                for tool, result in quality.tool_results.items():
                    if result.has_issues:
                        issues_count[tool] = issues_count.get(tool, 0) + 1
                        
        return issues_count

    def get_problem_analysis(self, problem_id: str) -> Dict:
        """Get detailed analysis for a specific problem."""
        if problem_id not in self.problems:
            raise ValueError(f"Problem {problem_id} not found in results")
            
        problem = self.problems[problem_id]
        return {
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

    def get_failed_test_cases(self, problem_id: str) -> List[str]:
        """Get list of failed test cases for a specific problem."""
        if problem_id not in self.problems:
            raise ValueError(f"Problem {problem_id} not found in results")
            
        test_cases = self.problems[problem_id].test_results['details'].test_cases
        return [test for test in test_cases if 'FAILED' in test]

    def get_submission_summary(self) -> Dict:
        """Get a high-level summary of the entire submission."""
        return {
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
