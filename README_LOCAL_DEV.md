# Local Development Database Setup

This guide explains how to run the local development database and related services for the Marking Assistant project.

## Prerequisites

- Docker and Docker Compose installed
- Git repository cloned locally
- Port 5432, 9000, 9001, and 5050 available on your machine

## Quick Start

### 1. Start the Development Services

```bash
# Start PostgreSQL, MinIO, and pgAdmin
docker-compose -f docker-compose.dev.yml up -d

# Check that services are running
docker-compose -f docker-compose.dev.yml ps
```

### 2. Initialize the Database Schema

The database tables will be automatically created when you run the core application:

```bash
# Navigate to the core directory
cd core

# Install dependencies (if not already done)
pip install -r ../requirements.txt

# Run the core application to initialize database
python main.py
```

The FastAPI application will:
- Connect to the PostgreSQL database
- Create all tables defined in the SQLModel models
- Start the API server on http://localhost:8000

### 3. Verify Setup

**Database Connection:**
```bash
# Connect to PostgreSQL directly
docker exec -it postgres_dev psql -U marking_user -d marking_assistant

# List tables
\dt

# Exit
\q
```

**MinIO Storage:**
- Console: http://localhost:9001
- API: http://localhost:9000
- Login: `minioadmin` / `minioadmin123`

**pgAdmin (Database Management UI):**
- URL: http://localhost:5050
- Login: `admin@example.com` / `admin123`

**Core API:**
- URL: http://localhost:8000
- Docs: http://localhost:8000/docs

## Service Details

### PostgreSQL Database
- **Container:** `postgres_dev`
- **Port:** 5432
- **Database:** `marking_assistant`
- **User:** `marking_user`
- **Password:** `marking_password`
- **Read-only User:** `readonly_user` / `readonly_pass`

### MinIO Object Storage
- **Container:** `minio_dev`
- **API Port:** 9000
- **Console Port:** 9001
- **Access Key:** `minioadmin`
- **Secret Key:** `minioadmin123`

### pgAdmin (Optional)
- **Container:** `pgadmin_dev`
- **Port:** 5050
- **Email:** `admin@example.com`
- **Password:** `admin123`

## Database Schema

The database schema is automatically created from the SQLModel definitions in the `core/models/` directory:

- **user** - User accounts and authentication
- **course** - Course information
- **task** - Assignment/task definitions
- **task_solution** - Student submissions
- **rubric_config** - Grading rubric configurations
- **user_course** - User-course relationships

## Development Workflow

### Running Tests with Database

```bash
# Start the database
docker-compose -f docker-compose.dev.yml up -d postgres

# Run tests that require database
cd marking_assistant
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_assignments.py -v
```

### Resetting the Database

```bash
# Stop and remove containers with data
docker-compose -f docker-compose.dev.yml down -v

# Start fresh
docker-compose -f docker-compose.dev.yml up -d

# Re-initialize schema by running the core app
cd core && python main.py
```

### Viewing Database Data

**Using psql:**
```bash
docker exec -it postgres_dev psql -U marking_user -d marking_assistant

# View users
SELECT * FROM "user";

# View tasks
SELECT * FROM task;

# View submissions
SELECT * FROM task_solution;
```

**Using pgAdmin:**
1. Open http://localhost:5050
2. Login with `admin@example.com` / `admin123`
3. Add New Server:
   - Name: `Local Dev`
   - Host: `postgres_dev`
   - Port: `5432`
   - Database: `marking_assistant`
   - Username: `marking_user`
   - Password: `marking_password`

## Environment Configuration

The development environment uses the `local.env` file for configuration. Key variables:

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=marking_assistant
DB_USER=marking_user
DB_PASSWORD=marking_password

# Storage
STORAGE_ENDPOINT=localhost:9000
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin123

# Security
JWT_ACCESS_SECRET=your-secret-here
JWT_REFRESH_SECRET=your-secret-here
DEBUG=true
```

## Troubleshooting

### Port Conflicts
If ports are already in use, modify the docker-compose.dev.yml file:
```yaml
ports:
  - "15432:5432"  # Change 5432 to 15432
```

Then update `local.env`:
```env
DB_PORT=15432
```

### Database Connection Issues
```bash
# Check if database is running
docker-compose -f docker-compose.dev.yml ps

# View database logs
docker logs postgres_dev

# Restart database
docker-compose -f docker-compose.dev.yml restart postgres
```

### MinIO Access Issues
```bash
# Check MinIO logs
docker logs minio_dev

# Create bucket if needed
# Access http://localhost:9001 and create 'marking-ai' bucket
```

## Production vs Development

| Aspect | Production | Development |
|--------|------------|-------------|
| Database Host | `postgres` | `localhost` |
| Persistent Volumes | `/opt/postgres/data` | Docker volume `postgres_data` |
| Network | External `backend-network` | Internal `dev-network` |
| Database Access | Container-only | Exposed port 5432 |
| pgAdmin | Not included | Included for debugging |

## Next Steps

Once your local database is running:

1. **Test the integration**: Run the marking assistant tests
2. **Add sample data**: Create test users, tasks, and submissions
3. **Develop new features**: Use the local database for development
4. **Debug issues**: Use pgAdmin to inspect data and queries

For questions or issues, check the main project README or create an issue in the repository. 