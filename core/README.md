# Core Module


## Scenarios
### 1. Login
```mermaid
sequenceDiagram
    actor User as Tutor/Student
    participant Panel
    participant Core
    participant Database
    
    User->>Panel: Login
    Panel->>Core: Authenticate (JWT)
    Core->>Database: Validate Credentials
    Database-->>Core: Return User Info (role)
    Core-->>Panel: Authentication Success
    Panel-->>User: Show Tutor/Student Dashboard
```

### 2. User submits code for assessment 
```mermaid
sequenceDiagram
    actor User as Tutor/Student
    participant Panel
    participant Core
    participant Database
    participant Moodle
    participant MarkingAssistant
    participant S3
    
    alt Upload manually
        User->>Panel: Upload Code
        Panel->>Core: Submit Code for Processing
    else Import from Moodle
        User->>Panel: Request Import from Moodle
        Panel->>Core: Request Moodle Data
        Core->>Moodle: Fetch User Submission
        Moodle-->>Core: Return Code Files
    end
    
    Core->>S3: Store Code Files
    Core->>Database: Store Submission Metadata
    Core->>MarkingAssistant: Run Linting, Tests, Plagiarism Check
    MarkingAssistant-->>Core: Return Analysis & Feedback
    Core->>Database: Store Feedback & Scores
    Core-->>Panel: Provide Feedback & Scores
    Panel-->>User: Display Feedback
```

### 3. Student views performance dashboard
```mermaid
sequenceDiagram
    actor S as Student
    participant P as Panel
    participant Core
    participant DB as Database

    
    S->>P: Navigate to Performance Dashboard
    P->>Core: Request Performance Data
    Core->>DB: Fetch Scores & Feedback History
    DB-->>Core: Return Data
    Core-->>P: Send Stats (Scores, Trends)
    P-->>S: Display Dashboard (Graphs, Insights)
```

### 4. Tutor monitors classes performance
```mermaid
sequenceDiagram
    actor Tutor
    participant Panel
    participant Core
    participant Database

    Tutor->>Panel: Access Dashboard
    Panel->>Core: Fetch Class Performance Data
    Core->>Database: Retrieve Class Performance Metrics
    Database-->>Core: Return Performance Insights
    Core-->>Panel: Show Class Metrics
    Panel-->>Tutor: Display Performance Data
```

### 5. Tutor defines/modify assignment
```mermaid
sequenceDiagram
    actor Tutor
    participant Panel
    participant Core
    participant Database
    participant S3

    Tutor->>Panel: Create/Modify Assignment
    Panel->>Core: CRUD Assignment <br/>(Rules/Configs/UnitTests)
    Core->>Database: Store/Update Assignment Data
    Core->>S3: Store/Update Assignment Files
    Core-->>Panel: Assignment Updated
    Panel-->>Tutor: Assignment Data
```