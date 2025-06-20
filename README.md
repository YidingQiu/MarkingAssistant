# Marking Assistant

> An automated system for assessing student code submissions with comprehensive feedback powered by LLMs

## Project Overview

This project aims to create an intelligent system that automates the assessment of student code submissions for programming labs and tutorials. By combining automated testing, code quality analysis, and LLM-based feedback, the system provides consistent, detailed feedback to help students improve their coding and mathematical abilities.

## System Design

The system consists of three primary modules and a Moodle integration component:

### 1. Assignment Marker Module

This module handles the intake and organization of student submissions:

- Moodle Assignment Loader: Downloads and organizes submissions from Moodle
- Folder Structure Parser: Processes the folder structure containing student submissions
- Student Code Extractor: Extracts Python files from student submissions
- Rubric Repository: Stores assessment rubrics for different labs/tutorials and questions

### 2. Code Testing Module

This module evaluates the correctness and quality of student code:

- PyTest Engine: Runs test cases against student code submissions
- Test Results Collector: Gathers the results of test runs
- Code Quality Tools: Performs linting and style checking (e.g., flake8, pylint, black)
- Static Analysis Reports: Generates reports on code quality issues

### 3. LLM Feedback Module

This module leverages locally deployed LLMs to generate intelligent feedback:

- Local LLM Deployment: Integration with Ollama and other models (Qwen/QwQ)
- Rubric Analyzer: Analyzes code against assessment rubrics
- Test Result Analyzer: Analyzes test results to understand code correctness
- Initial Feedback Generator: Creates detailed feedback based on test results
- Integrated Score Generator: Calculates scores based on code quality, test results, and feedback context
- Score + Feedback Aligner: Ensures consistency between numerical scores and narrative feedback

### 4. Moodle Integration

This component automates the delivery of feedback:

- Automation Script: Scripts that interface with Moodle
- Student Marking Page Navigator: Navigates to individual student marking pages
- Score & Feedback Uploader: Uploads the final assessment to Moodle

## Architecture Diagrams


### Process Flow

```mermaid
flowchart TD
    Start([Start]) --> DownloadMoodle[Download Submissions from Moodle]
    DownloadMoodle --> ExtractFiles[Extract Student Folders]
    ExtractFiles --> LoadRubrics[Load Assessment Rubrics]
    
    ExtractFiles --> ParseCode[Parse Python Files]
    ParseCode --> RunTests[Run PyTest Test Cases]
    ParseCode --> RunLinting[Run Code Style/Linting]
    
    RunTests --> CollectResults[Collect Test Results]
    RunLinting --> CollectStyleIssues[Collect Style Issues]
    
    LoadRubrics --> RubricAnalysis[LLM Rubric Analysis]
    ParseCode --> RubricAnalysis
    
    CollectResults --> TestResultAnalysis[LLM Test Result Analysis]
    CollectStyleIssues --> TestResultAnalysis
    TestResultAnalysis --> GenerateFeedback[Generate Initial Feedback]
    
    RubricAnalysis --> GenerateScores[Generate Aligned Scores]
    CollectResults --> GenerateScores
    GenerateFeedback --> GenerateScores
    
    GenerateScores --> ComposeResults[Compose Final Assessment]
    GenerateFeedback --> ComposeResults
    ComposeResults --> GenerateReport[Generate Student Report]
    
    GenerateReport --> AutomateMoodle[Run Moodle Automation Script]
    AutomateMoodle --> NavigatePages[Navigate to Marking Pages]
    NavigatePages --> UploadFeedback[Upload Scores & Feedback]
    UploadFeedback --> End([End])
    
    subgraph "LLM Processing"
        RubricAnalysis
        TestResultAnalysis
        GenerateScores
        GenerateFeedback
        ComposeResults
    end
    
    subgraph "Testing & Analysis"
        RunTests
        RunLinting
        CollectResults
        CollectStyleIssues
    end
    
    subgraph "Moodle Integration"
        AutomateMoodle
        NavigatePages
        UploadFeedback
    end
```

### System Architecture

```mermaid
sequenceDiagram
    participant MP as Marker Module
    participant TP as Test Module
    participant RA as Rubric Analyzer LLM
    participant TRA as Test Result Analyzer LLM
    participant SA as Scoring Agent LLM
    participant CA as Composition Agent LLM
    participant MI as Moodle Integration
    
    MP->>RA: Send Student Code
    MP->>RA: Send Assessment Rubric
    TP->>TRA: Send Test Results
    TP->>TRA: Send Style Analysis
    
    RA->>RA: Analyze Code Against Rubric
    TRA->>TRA: Analyze Test Results
    TRA->>TRA: Generate Initial Feedback
    
    RA->>SA: Send Code Analysis
    TRA->>SA: Send Test Results
    TRA->>SA: Send Initial Feedback
    
    SA->>SA: Calculate Scores Based on Code Quality, Test Results, and Feedback Context
    
    SA->>CA: Send Score Assessment
    TRA->>CA: Send Detailed Feedback
    
    CA->>CA: Align Feedback with Scores
    CA->>CA: Compose Final Assessment
    CA->>MI: Send Combined Scores & Feedback
    
    Note over RA: Multiple LLMs can be used (Qwen/QwQ, LLaMA, etc.)
    Note over TRA: Multiple LLMs can be used
    Note over SA: Multiple LLMs can be used
    Note over CA: Final assessment includes numeric scores aligned with feedback, strengths & weaknesses, and improvement suggestions
```


### LLM Agent Interaction

```mermaid
graph TD
    subgraph "Assignment Marker Module"
        A1[Moodle Assignment Loader] --> A2[Folder Structure Parser]
        A2 --> A3[Student Code Extractor]
        R1[Rubric Repository] --> R2[Lab/Tutorial Specific Rubrics]
        R2 --> R3[Question-Level Criteria]
    end

    subgraph "Code Testing Module"
        T1[PyTest Engine] --> T2[Test Case Runner]
        T2 --> T3[Test Results Collector]
        L1[Code Quality Tools] --> L2[Linting & Style Checker]
        L2 --> L3[Static Analysis Reports]
    end

    subgraph "LLM Feedback Module"
        
        A1[Assessment Agent] --> A2R[Rubric Analyzer]
        
        F1[Feedback Agent] --> F2[Test Result Analyzer]
        F2 --> F3[Initial Feedback Generator]
        
        S1[Scoring Agent] --> S2[Integrated Score Generator]
        A2R --> S1
        F2 --> S1
        F3 --> S1
        
        C1[Composition Agent] --> C2[Score + Feedback Aligner]
    end

    A3 --> T1
    A3 --> L1
    T3 --> F1
    L3 --> F1
    R3 --> A1
    A3 --> A1

    subgraph "Moodle Integration"
        MI1[Automation Script]
        MI2[Student Marking Page Navigator]
        MI3[Score & Feedback Uploader]
    end

    C2 --> MI1
    MI1 --> MI2
    MI2 --> MI3
```

## Requirements

### Functional Requirements

1. **Submission Processing**
   - Parse folder structures from Moodle
   - Extract Python files from student submissions
   - Load and apply appropriate rubrics based on lab/tutorial

2. **Code Assessment**
   - Run automated test cases against student code
   - Perform code style and quality analysis
   - Generate test result reports

3. **Intelligent Feedback**
   - Analyze code against rubrics using LLMs
   - Generate detailed feedback based on test results
   - Produce scores that align with both code quality and correctness
   - Create comprehensive assessment reports

4. **Moodle Integration**
   - Navigate through Moodle's interface
   - Upload scores and feedback to appropriate locations
   - Maintain session state during batch processing

### Technical Requirements

1. **Python-Based Architecture**
   - Core system written in Python
   - Support for running and analyzing Python student submissions

2. **LLM Integration**
   - Local deployment using Ollama
   - Support for multiple models (Qwen/QwQ-32B, LLaMA3.1, etc.)
   - Structured prompt templates for different analysis tasks

3. **Testing Framework**
   - PyTest-based test case execution
   - Structured test result collection
   - Support for custom test case definitions per assignment

4. **Web Automation**
   - Browser automation for Moodle interaction
   - Session management and authentication

## Usage Guide

### Running the Marking Pipeline

The marking pipeline can be run using the following command:

```bash
python marking_pipeline.py --task-name <task_name> [options]
```

#### Required Arguments:
- `--task-name`: Name of the task to process (e.g., Lab1, Ass2, "ZEIT1307-5254_00067_Lab 1_submission")
  - This corresponds to a key in the config file and a folder in the submissions directory.

#### Optional Arguments:
- `--submissions-dir`: Path to the base submissions directory (default: 'submissions')
  - Expected structure: `submissions_dir / task_name / user_submission_folder`
- `--config-file`: Path to the main YAML configuration file defining tasks (default: 'rubric/marking_config.yaml')
- `--model`: Name of the LLM model to use for feedback generation (default: 'openai-gpt-4o') # Default might vary
- `--feedback-format`: Format of the generated feedback (choices: html, markdown, text; default: markdown)
- `--log-level`: Set the logging level (choices: DEBUG, INFO, WARNING, ERROR, CRITICAL; default: INFO)
- `--log-file`: Path to log file (default: marking_pipeline.log)
- `--skip-feedback`: Skip feedback generation and only run tests
- `--skip-tests`: Skip test running and only generate feedback
- `--test-timeout`: Maximum time in seconds allowed for running tests for a single problem/task (default: 30)

#### Example Usage:

1. Basic usage for a specific task named "Lab1":
```bash
python marking_pipeline.py --task-name Lab1
```

2. Process a task with a name containing spaces, specifying directories:
```bash
python marking_pipeline.py --task-name "Ass2 Part 1" --submissions-dir "path/to/all_submissions" --config-file "path/to/main_config.yaml"
```

3. Skip feedback generation for "Lab3":
```bash
python marking_pipeline.py --task-name Lab3 --skip-feedback
```

4. Use a different LLM model and feedback format for "Ass1":
```bash
python marking_pipeline.py --task-name Ass1 --model llama --feedback-format html
```

#### Directory Structure:
The pipeline generally expects and uses a structure like this:
```
.
├── submissions/          # Base directory for all task submissions
│   ├── Task1/           # Submissions specifically for Task1
│   │   └── UserFolder1/
│   │   └── UserFolder2/
│   └── Task2/           # Submissions specifically for Task2
│       └── ...
├── rubric/               # Base directory for configuration and tests
│   ├── marking_config.yaml # Main configuration file (or path specified by --config-file)
│   ├── test_cases/       # Test cases organized by task name
│   │   ├── Task1/
│   │   │   └── test_problem1.py
│   │   └── Task2/
│   │       └── ...
│   └── test_results/     # Test results organized by task name
│       ├── Task1/
│       │   └── User1_Task1_results.json
│       └── Task2/
│           └── ...
├── feedback/             # Generated feedback organized by task name
│   ├── Task1/
│   │   └── User1_Task1_feedback.md
│   └── Task2/
│       └── ...
└── marking_pipeline.log  # Log file
```

#### Output:
- Test results are stored in `rubric/test_results/<task_name>/` (or similar structure defined in test runner)
- Feedback is generated in `feedback/<task_name>/`
- Detailed logs are written to `marking_pipeline.log` (or file specified by --log-file)

## Planned Development Phases

1. **Phase 1**: Core modules development
   - Assignment marker module implementation
   - Test execution framework
   - Basic LLM integration

2. **Phase 2**: LLM feedback enhancement
   - Multi-agent LLM architecture
   - Scoring alignment with feedback
   - Feedback quality improvements

3. **Phase 3**: Moodle integration
   - Browser automation development
   - Score and feedback uploading
   - End-to-end testing

## License

[TBD]
