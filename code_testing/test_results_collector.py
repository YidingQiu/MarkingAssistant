from code_testing.pytest_engine import run_tests


def summarize_results(test_results):
    """Summarize the results of the test runs."""
    summary = {
        'passed': len([r for r in test_results if r == 0]),
        'failed': len([r for r in test_results if r != 0]),
        'total': len(test_results)
    }
    return summary

def collect_and_summarize(test_directory):
    """Collect test results and summarize them."""
    results = run_tests(test_directory)  # Assuming this returns a list of results
    return summarize_results(results)
