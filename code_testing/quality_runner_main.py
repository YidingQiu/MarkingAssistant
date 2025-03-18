import os
from code_testing.code_quality_tools import run_flake8, run_black #, run_pylint

def format_tool_output(output):
    """Format tool output to ensure consistent line endings and remove trailing whitespace."""
    if output is None:
        return None
    if isinstance(output, list):
        # Handle flake8's statistics list
        return [str(item) for item in output]
    return str(output).replace('\r\n', '\n').replace('\r', '\n').strip()

def run_quality_checks(file_path):
    """Run all code quality checks on a file and return results."""
    quality_results = {}
    
    # Run flake8
    flake8_output = run_flake8(file_path)
    has_flake8_issues = flake8_output != "No style issues found"
    quality_results['flake8'] = {
        'name': 'Flake8',
        'description': 'Style Guide Enforcement',
        'output': format_tool_output(flake8_output),
        'has_issues': has_flake8_issues,
        'warning': None
    }
    
    # # Run pylint
    # try:
    #     pylint_output = run_pylint(file_path)
    #     quality_results['pylint'] = {
    #         'name': 'Pylint',
    #         'description': 'Code Analysis',
    #         'output': format_tool_output(pylint_output),
    #         'has_issues': pylint_output != "No issues found",
    #         'error': None
    #     }
    # except Exception as e:
    #     quality_results['pylint'] = {
    #         'name': 'Pylint',
    #         'description': 'Tool execution failed',
    #         'output': None,
    #         'has_issues': True,
    #         'error': str(e)
    #     }
    
    # Run black
    black_output = run_black(file_path)
    formatted_black_output = format_tool_output(black_output)
    
    # Determine if there are actual formatting issues
    has_black_issues = black_output.startswith('Code formatting issues found')
    
    quality_results['black'] = {
        'name': 'Black',
        'description': 'Code Formatting',
        'output': formatted_black_output,
        'has_issues': has_black_issues,
        'warning': None
    }
    
    return quality_results 