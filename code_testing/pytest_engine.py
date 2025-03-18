import pytest
import os

def run_tests(test_directory):
    """Run all tests in the specified directory and return the results."""
    pytest_args = [test_directory]
    result = pytest.main(pytest_args)
    return result

def collect_test_results(test_directory):
    """Collect results from the test runs."""
    # This can be expanded to collect detailed results
    result = run_tests(test_directory)
    return result
