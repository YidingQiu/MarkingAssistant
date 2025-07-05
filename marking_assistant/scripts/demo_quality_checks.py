#!/usr/bin/env python3
"""
Demo script to show how the quality check system works.
This demonstrates the criteria used to flag problematic submissions.
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def demo_quality_checks():
    """Demonstrate the quality check criteria and examples."""
    
    print("=" * 80)
    print("SUBMISSION QUALITY CHECK SYSTEM")
    print("=" * 80)
    
    print("\n🎯 PURPOSE:")
    print("   Automatically identify students whose submissions may have problems")
    print("   and require manual review of the original submission files.")
    
    print("\n🚨 DETECTION CRITERIA:")
    print("=" * 50)
    
    criteria = [
        {
            "name": "Very Low Total Score",
            "condition": "< 10% of maximum possible score",
            "example": "Student scored 15/200 (7.5%)",
            "likely_cause": "Missing files, corrupted submission, wrong format"
        },
        {
            "name": "Too Many Zero Scores",
            "condition": "≥ 50% of modules scored zero",
            "example": "12 out of 24 modules got 0 points",
            "likely_cause": "Incomplete submission, missing required files"
        },
        {
            "name": "No Test Results",
            "condition": "No tests found or all tests failed",
            "example": "0/15 tests passed (0% pass rate)",
            "likely_cause": "Code doesn't run, syntax errors, missing dependencies"
        },
        {
            "name": "Processing Errors",
            "condition": "≥ 3 score extraction errors",
            "example": "5 modules failed to extract scores",
            "likely_cause": "Malformed responses, parsing issues"
        },
        {
            "name": "Missing Information",
            "condition": "Student name or feedback missing",
            "example": "Student name shows as 'Unknown'",
            "likely_cause": "File naming issues, processing problems"
        }
    ]
    
    for i, criterion in enumerate(criteria, 1):
        print(f"\n{i}. {criterion['name'].upper()}")
        print(f"   Condition: {criterion['condition']}")
        print(f"   Example:   {criterion['example']}")
        print(f"   Likely:    {criterion['likely_cause']}")
    
    print("\n" + "=" * 80)
    print("VISUAL INDICATORS IN EXCEL")
    print("=" * 80)
    
    print("\n📊 IN THE MAIN WORKSHEET:")
    print("   • Entire row highlighted in light red background")
    print("   • Problem_Summary column shows warning in bold red text")
    print("   • Row height increased for better visibility")
    print("   • Warning message: '⚠️ POTENTIAL SUBMISSION PROBLEMS - Please check original submission file'")
    
    print("\n📈 IN THE SUMMARY WORKSHEET:")
    print("   • 'Submission Quality Check' section at the top")
    print("   • Count of problematic students highlighted in red")
    print("   • List of specific students requiring attention")
    print("   • Individual problem descriptions for each flagged student")
    
    print("\n" + "=" * 80)
    print("EXAMPLE PROBLEM MESSAGES")
    print("=" * 80)
    
    examples = [
        "Very low total score (8.2%); 15/24 modules scored zero (62.5%)",
        "All 12 tests failed; 4 score extraction errors",
        "Very low total score (3.1%); No test results found",
        "18/24 modules scored zero (75.0%); Missing student information"
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example}")
    
    print("\n" + "=" * 80)
    print("MARKER WORKFLOW")
    print("=" * 80)
    
    workflow = [
        "1. Open the Excel report",
        "2. Check the 'Summary Statistics' sheet for problem count",
        "3. Look for red-highlighted rows in the main sheet",
        "4. Read the Problem_Summary column for specific issues",
        "5. For flagged students, manually check:",
        "   • Original submission files",
        "   • File formats and completeness", 
        "   • Code syntax and structure",
        "   • Whether files were submitted correctly",
        "6. Consider re-running the pipeline if issues are found",
        "7. Manually adjust scores if submission was valid but had processing issues"
    ]
    
    for step in workflow:
        print(f"   {step}")
    
    print("\n" + "=" * 80)
    print("BENEFITS")
    print("=" * 80)
    
    benefits = [
        "✅ Saves time by automatically flagging potential issues",
        "✅ Reduces risk of missing problematic submissions",
        "✅ Provides clear guidance on what to check manually",
        "✅ Helps ensure fair grading for all students",
        "✅ Visual indicators make problems immediately obvious",
        "✅ Detailed warnings help diagnose specific issues"
    ]
    
    for benefit in benefits:
        print(f"   {benefit}")
    
    print("\n" + "=" * 80)
    print("USAGE EXAMPLE")
    print("=" * 80)
    
    print("""
# Generate Excel report with quality checks
python scripts/excel_summary.py \\
  --task-name "Assignment_3" \\
  --output-dir reports

# The generated Excel will automatically include:
# • Quality check columns (Has_Problems, Problem_Summary, etc.)
# • Visual highlighting of problematic submissions
# • Summary statistics with problem counts
# • Detailed warnings for each flagged student
    """)
    
    print("=" * 80)


if __name__ == "__main__":
    demo_quality_checks() 