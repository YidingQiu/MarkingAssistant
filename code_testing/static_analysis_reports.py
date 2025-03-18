def generate_report(quality_results):
    """Generate a static analysis report based on quality results."""
    report = "Static Analysis Report\n"
    report += "=" * 30 + "\n"
    report += quality_results
    return report

def save_report(report, file_path):
    """Save the report to a file."""
    with open(file_path, 'w') as f:
        f.write(report)
