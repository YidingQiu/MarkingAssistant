# Score Extraction and CSV Generation

This document explains how to use the new PydanticAI-based score extraction and CSV generation functionality that has been added to the marking pipeline.

## Overview

The system now includes:
1. **Automatic score extraction** from LLM intermediate responses using PydanticAI
2. **CSV report generation** that combines scores, test results, quality metrics, and feedback data
3. **Standalone scripts** for processing existing data

## Components

### 1. Score Extraction (`ScoreExtractor`)

Located in `src/marking_assistant/analysis/score_extractor.py`

- Extracts scores from intermediate JSON response files
- Uses direct JSON parsing and regex patterns to find scores
- Aggregates scores across all modules for each student
- Saves results to `results/{task_name}/scores_summary.json`

### 2. CSV Generation (`SummaryCSVGenerator`)

Located in `scripts/summary_csv.py`

- Generates comprehensive CSV reports from multiple data sources
- Combines scores, test results, quality metrics, and feedback information
- Creates both summary and detailed reports

## Usage

### Integrated with Marking Pipeline

The score extraction is now automatically integrated into the main marking pipeline. When you run the pipeline, it will:

1. Execute all modules and save intermediate responses
2. Extract scores from the intermediate responses
3. Save a `scores_summary.json` file in the results directory

### Standalone Score Extraction

To extract scores from existing intermediate responses:

```bash
python scripts/extract_scores.py \
  --task-name "ZEIT1307-5254_00067_Assignment 3 (due 2355 8 June)_submission" \
  --config-file "rubric/tasks/ZEIT1307-5254_00067_Assignment 3 (due 2355 8 June)_submission.yaml"
```

Options:
- `--task-name`: Name of the task to process
- `--config-file`: Path to task configuration (to extract max scores)
- `--intermediate-dir`: Directory containing intermediate responses (default: `results/intermediate_responses`)
- `--results-dir`: Directory to save extracted scores (default: `results`)

### CSV Report Generation

To generate CSV reports from the extracted data:

```bash
python scripts/summary_csv.py \
  --task-name "ZEIT1307-5254_00067_Assignment 3 (due 2355 8 June)_submission" \
  --output-dir reports
```

Options:
- `--task-name`: Name of the task to generate reports for
- `--results-dir`: Directory containing results data (default: `results`)
- `--feedback-dir`: Directory containing feedback files (default: `feedback`)
- `--output-dir`: Directory to save CSV reports (default: `reports`)
- `--summary-only`: Generate only the summary CSV
- `--detailed-only`: Generate only the detailed scores CSV

## Output Files

### Scores Summary JSON

`results/{task_name}/scores_summary.json` contains:
- Student summaries with total scores and percentages
- Individual module scores with justifications
- Extraction errors and metadata

### CSV Reports

1. **Summary CSV**: One row per student with:
   - Student information (ID, name)
   - Total scores and percentages
   - Test results summary
   - Quality metrics summary
   - Feedback information

2. **Detailed Scores CSV**: One row per module per student with:
   - Individual module scores and justifications
   - Module-level performance data

## Data Sources

The system combines data from:
- `results/{task_name}/scores_summary.json` (extracted scores)
- `results/{task_name}/*_test_results.json` (test results)
- `results/{task_name}/*_quality_results.json` (quality metrics)
- `feedback/{task_name}/*.md` (feedback reports)

## Configuration

### Module Max Scores

The system automatically extracts maximum scores from the task configuration YAML file by looking for patterns like:
- `(X points)`
- `X points total`
- `Assessment Focus: ... (X points)`

You can also provide fallback scores based on module naming patterns.

### Score Extraction Patterns

The score extractor looks for various patterns in LLM responses:
- JSON with `score` field (direct extraction)
- Text patterns like `score: X`, `X/Y`, `awarded: X`
- Fallback to regex patterns for complex responses

## Example Workflow

1. Run the marking pipeline (scores are automatically extracted):
   ```bash
   python scripts/run_marking.py --task-name "Assignment_3"
   ```

2. Generate CSV reports:
   ```bash
   python scripts/summary_csv.py --task-name "Assignment_3" --output-dir reports
   ```

3. View results:
   - Summary: `reports/summary_Assignment_3_YYYYMMDD_HHMMSS.csv`
   - Detailed: `reports/detailed_scores_Assignment_3_YYYYMMDD_HHMMSS.csv`

## Troubleshooting

### Common Issues

1. **Missing scores**: Check that intermediate responses exist and contain valid JSON
2. **Incorrect max scores**: Verify the task configuration YAML has proper score annotations
3. **Missing student names**: Ensure feedback files follow the naming convention or contain student names in content

### Debugging

- Check the `scores_summary.json` file for extraction errors
- Review intermediate response files for parsing issues
- Verify file paths and naming conventions match expected patterns

## Dependencies

- `pydantic-ai`: For structured LLM interactions (if using advanced extraction)
- `pandas`: For CSV generation
- `pyyaml`: For configuration file parsing
- `pathlib`: For file system operations 