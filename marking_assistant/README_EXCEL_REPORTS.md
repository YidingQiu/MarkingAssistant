# Excel Comprehensive Reports

This document explains the Excel reporting functionality that creates comprehensive, formatted Excel files with complete student data.

## Overview

The Excel generator creates a single, comprehensive Excel file with:
- **One student per row** with all related information in columns
- **Full feedback text** (not truncated) in dedicated cells
- **Module scores with justifications** in adjacent columns
- **Professional formatting** with proper styling and layout
- **Summary statistics** in a separate worksheet

## Key Features

### ✅ **Complete Data Integration**
- Student information (ID, name, task)
- Total scores and percentages
- Individual module scores with justifications
- Test results and quality metrics
- **Full feedback text** (up to 32,767 characters per cell)

### ✅ **Excel-Optimized Layout**
- **One student per row** for easy analysis
- **Module score followed by justification** in adjacent columns
- **Text wrapping** for long content (justifications, feedback)
- **Frozen panes** for easy navigation
- **Professional styling** with headers, borders, and colors

### ✅ **Dual Worksheet Design**
1. **Student Summary**: Complete data table
2. **Summary Statistics**: Overview and analytics

### ✅ **Submission Quality Checks**
- **Automatic problem detection** for low scores and submission issues
- **Visual highlighting** of problematic submissions in red
- **Warning messages** to guide marker attention
- **Summary of issues** in the statistics worksheet

## Quality Check Criteria

The system automatically flags submissions that may have problems:

### 🚨 **Low Score Detection**
- **Total score < 10%** of maximum possible
- Indicates potential submission or processing issues

### 🚨 **Zero Score Pattern**
- **50% or more modules** scored zero
- Suggests missing or corrupted submission files

### 🚨 **Test Failure Issues**
- **No test results** found for the student
- **All tests failed** (0% pass rate)

### 🚨 **Processing Problems**
- **3+ score extraction errors** during processing
- **Missing student information** or feedback

### 🚨 **Visual Indicators**
- **Red highlighting** of entire row for problematic submissions
- **Bold red text** in problem summary column
- **Warning messages** like: "⚠️ POTENTIAL SUBMISSION PROBLEMS - Please check original submission file"

## Column Structure

The Excel file includes these column groups:

### Basic Information
- `Student_ID`: Student identifier
- `Student_Name`: Full student name
- `Task_Name`: Assignment/task name
- `Submission_Date`: Processing date

### Overall Scores
- `Total_Score`: Sum of all module scores
- `Max_Total_Score`: Maximum possible total
- `Percentage_Score`: Overall percentage
- `Module_Count`: Number of modules evaluated
- `Extraction_Errors`: Number of processing errors

### Test Results
- `Test_Total`: Total number of tests
- `Test_Passed`: Number of passed tests
- `Test_Failed`: Number of failed tests
- `Test_Pass_Rate`: Percentage of tests passed
- `Test_Score`: Test-based score

### Quality Metrics
- `Quality_Code_Score`: Overall code quality
- `Quality_Complexity`: Code complexity score
- `Quality_Documentation`: Documentation quality
- `Quality_Style_Issues`: Number of style issues

### Module Scores (for each module)
- `Module_{module_id}_Score`: Points awarded
- `Module_{module_id}_Max`: Maximum possible points
- `Module_{module_id}_Percentage`: Module percentage
- `Module_{module_id}_Success`: Whether evaluation succeeded
- `Module_{module_id}_Justification`: **Full justification text**

### Feedback Information
- `Has_Feedback`: Whether feedback exists
- `Feedback_Length`: Character count of feedback
- `Feedback_File_Path`: Path to original feedback file
- `Full_Feedback_Text`: **Complete feedback content**

### Submission Quality Checks
- `Has_Problems`: Boolean flag for potential submission issues
- `Problem_Summary`: **Warning message for markers**
- `Detailed_Warnings`: Specific issues detected
- `Warning_Count`: Number of warnings generated
- `Warning_Flags`: JSON object with specific problem flags
- `Individual_Warnings`: JSON array of individual warning messages

## Usage

### Generate Excel Report

```bash
python scripts/excel_summary.py \
  --task-name "ZEIT1307-5254_00067_Assignment 3 (due 2355 8 June)_submission" \
  --output-dir reports
```

### Command Options

- `--task-name`: Name of the task to process (required)
- `--results-dir`: Directory containing results data (default: `results`)
- `--feedback-dir`: Directory containing feedback files (default: `feedback`)
- `--output-file`: Specific output file path (optional)
- `--output-dir`: Directory to save report (default: `reports`)

### Example with Custom Output

```bash
python scripts/excel_summary.py \
  --task-name "Assignment_3" \
  --output-file "grading/assignment3_comprehensive.xlsx"
```

## Excel Features

### 📊 **Professional Formatting**
- **Header styling**: Blue background, white text, bold font
- **Cell borders**: Clean table appearance
- **Text wrapping**: Automatic for long content
- **Column sizing**: Optimized widths for different content types
- **Row heights**: Adequate space for wrapped text

### 🔒 **Navigation Aids**
- **Frozen panes**: First 4 columns and header row stay visible
- **Column grouping**: Related data grouped logically
- **Consistent naming**: Predictable column names for filtering

### 📈 **Summary Statistics Sheet**
- Task overview and metadata
- Score distribution statistics
- Module performance averages
- Student performance bands

## Handling Long Content

### Full Feedback Text
- **No truncation**: Complete feedback preserved
- **Text wrapping**: Automatic line breaks in cells
- **Wide columns**: 50-character width for readability
- **Vertical alignment**: Top-aligned for multi-line content

### Module Justifications
- **Complete justifications**: Full LLM reasoning preserved
- **Adjacent placement**: Score followed immediately by justification
- **Searchable content**: Excel's find function works across all text

## Data Sources

The Excel generator combines data from:
- `results/{task_name}/scores_summary.json`
- `results/{task_name}/*_test_results.json`
- `results/{task_name}/*_quality_results.json`
- `feedback/{task_name}/*.md`

## Excel File Structure

```
comprehensive_TaskName_YYYYMMDD_HHMMSS.xlsx
├── Student Summary (main data sheet)
│   ├── Basic info columns (A-D)
│   ├── Overall scores (E-I)
│   ├── Test results (J-N)
│   ├── Quality metrics (O-R)
│   ├── Module scores & justifications (S-...)
│   └── Feedback columns (last columns)
└── Summary Statistics (analytics sheet)
    ├── Task metadata
    ├── Score statistics
    └── Module performance summary
```

## Advantages Over CSV

### ✅ **Rich Formatting**
- Professional appearance for presentations
- Color coding and styling
- Better readability

### ✅ **Multiple Worksheets**
- Separate summary statistics
- Organized data presentation
- Easy navigation between views

### ✅ **Excel Features**
- Filtering and sorting capabilities
- Formula support for custom calculations
- Charts and pivot tables (can be added manually)

### ✅ **Long Text Support**
- No truncation of feedback or justifications
- Proper text wrapping and formatting
- Searchable content across all cells

## Example Workflow

1. **Run marking pipeline** (generates all data):
   ```bash
   python scripts/run_marking.py --task-name "Assignment_3"
   ```

2. **Extract scores** (if not done automatically):
   ```bash
   python scripts/extract_scores.py --task-name "Assignment_3"
   ```

3. **Generate Excel report**:
   ```bash
   python scripts/excel_summary.py --task-name "Assignment_3"
   ```

4. **Open in Excel** for analysis, grading, and reporting

## Tips for Excel Usage

### 📋 **For Grading**
- Use Excel's filter feature to focus on specific modules
- Sort by percentage score to identify struggling students
- Use conditional formatting to highlight score ranges

### 📊 **For Analysis**
- Check the Summary Statistics sheet for overview
- Create pivot tables for deeper analysis
- Use Excel's chart features for visualizations

### 🔍 **For Review**
- Use Ctrl+F to search within justifications and feedback
- Freeze additional columns if needed for your workflow
- Adjust column widths based on your screen size

## Dependencies

- `openpyxl>=3.0.0`: Excel file creation and formatting
- `pandas>=1.5.0`: Data manipulation
- All other dependencies from the main pipeline

The Excel generator provides the most comprehensive and user-friendly format for reviewing student performance across all assessment dimensions! 