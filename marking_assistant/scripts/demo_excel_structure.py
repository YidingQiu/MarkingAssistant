#!/usr/bin/env python3
"""
Demo script to show the Excel structure and column layout.
This helps understand what the comprehensive Excel report contains.
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from marking_assistant.analysis.score_extractor import ScoreExtractor


def demo_excel_structure():
    """Demonstrate the Excel structure by showing column names and organization."""
    
    print("=" * 80)
    print("COMPREHENSIVE EXCEL REPORT STRUCTURE")
    print("=" * 80)
    
    print("\nBASIC INFORMATION COLUMNS:")
    basic_cols = [
        "Student_ID", "Student_Name", "Task_Name", "Submission_Date"
    ]
    for i, col in enumerate(basic_cols, 1):
        print(f"  {i:2d}. {col}")
    
    print("\nOVERALL SCORES COLUMNS:")
    score_cols = [
        "Total_Score", "Max_Total_Score", "Percentage_Score", 
        "Module_Count", "Extraction_Errors"
    ]
    for i, col in enumerate(score_cols, len(basic_cols) + 1):
        print(f"  {i:2d}. {col}")
    
    print("\nTEST RESULTS COLUMNS:")
    test_cols = [
        "Test_Total", "Test_Passed", "Test_Failed", 
        "Test_Pass_Rate", "Test_Score"
    ]
    for i, col in enumerate(test_cols, len(basic_cols) + len(score_cols) + 1):
        print(f"  {i:2d}. {col}")
    
    print("\nQUALITY METRICS COLUMNS:")
    quality_cols = [
        "Quality_Code_Score", "Quality_Complexity", 
        "Quality_Documentation", "Quality_Style_Issues"
    ]
    for i, col in enumerate(quality_cols, len(basic_cols) + len(score_cols) + len(test_cols) + 1):
        print(f"  {i:2d}. {col}")
    
    print("\nMODULE SCORES PATTERN (repeated for each module):")
    print("     For each module_id, you get 5 columns:")
    module_pattern = [
        "Module_{module_id}_Score",
        "Module_{module_id}_Max", 
        "Module_{module_id}_Percentage",
        "Module_{module_id}_Success",
        "Module_{module_id}_Justification"
    ]
    for i, col in enumerate(module_pattern, 1):
        print(f"       {i}. {col}")
    
    print("\nFEEDBACK COLUMNS (at the end):")
    feedback_cols = [
        "Has_Feedback", "Feedback_Length", 
        "Feedback_File_Path", "Full_Feedback_Text"
    ]
    base_count = len(basic_cols) + len(score_cols) + len(test_cols) + len(quality_cols)
    for i, col in enumerate(feedback_cols, 1):
        print(f"     {col}")
    
    print("\n" + "=" * 80)
    print("EXAMPLE MODULE COLUMNS (for Assignment 3):")
    print("=" * 80)
    
    # Show some example module IDs from Assignment 3
    example_modules = [
        "p1_data_loading", "p1_data_visualization", "p1a_logistic_model_function",
        "p1b_gaussian_model_function", "p2_data_loading", "p2_efficiency_analysis",
        "code_documentation_quality", "final_comprehensive_report"
    ]
    
    for module in example_modules[:5]:  # Show first 5 as examples
        print(f"\n {module.upper()}:")
        for pattern in module_pattern:
            col_name = pattern.format(module_id=module)
            print(f"     {col_name}")
    
    print(f"\n... and {len(example_modules) - 5} more modules with the same pattern")
    
    print("\n" + "=" * 80)
    print("KEY FEATURES:")
    print("=" * 80)
    
    features = [
        "✅ One student per row - easy to analyze and sort",
        "✅ Module score immediately followed by justification",
        "✅ Full feedback text preserved (no truncation)",
        "✅ Professional Excel formatting with headers and borders",
        "✅ Text wrapping for long justifications and feedback",
        "✅ Frozen panes for easy navigation",
        "✅ Summary statistics in separate worksheet",
        "✅ Searchable content across all text fields"
    ]
    
    for feature in features:
        print(f"  {feature}")
    
    print("\n" + "=" * 80)
    print("USAGE EXAMPLE:")
    print("=" * 80)
    
    print("""
python scripts/excel_summary.py \\
  --task-name "ZEIT1307-5254_00067_Assignment 3 (due 2355 8 June)_submission" \\
  --output-dir reports

This creates: reports/comprehensive_TaskName_YYYYMMDD_HHMMSS.xlsx
    """)
    
    print("=" * 80)


if __name__ == "__main__":
    demo_excel_structure() 