@echo off

rem Development Database Management Script for Windows
rem Usage: dev-db.bat [command]

set COMPOSE_FILE=docker-compose.dev.yml

if "%1"=="start" goto start_services
if "%1"=="stop" goto stop_services
if "%1"=="restart" goto restart_services
if "%1"=="reset" goto reset_database
if "%1"=="status" goto show_status
if "%1"=="logs" goto show_logs
if "%1"=="psql" goto connect_psql
if "%1"=="init-schema" goto init_schema
if "%1"=="test" goto run_tests
if "%1"=="clean" goto clean_all
if "%1"=="help" goto show_help
if "%1"=="--help" goto show_help
if "%1"=="-h" goto show_help
if "%1"=="" goto show_help
goto unknown_command

:show_help
echo Development Database Management Script
echo.
echo Usage: dev-db.bat [command]
echo.
echo Commands:
echo   start       - Start all development services
echo   stop        - Stop all development services
echo   restart     - Restart all development services
echo   reset       - Reset database (removes all data)
echo   status      - Show status of all services
echo   logs        - Show logs from all services
echo   psql        - Connect to PostgreSQL database
echo   init-schema - Initialize database schema (run core app)
echo   test        - Run tests with database
echo   clean       - Remove all containers and volumes
echo.
echo Service URLs:
echo   PostgreSQL:  localhost:5432
echo   MinIO API:   http://localhost:9000
echo   MinIO UI:    http://localhost:9001
echo   pgAdmin:     http://localhost:5050
echo   Core API:    http://localhost:8000
goto end

:start_services
echo 🚀 Starting development services...
docker-compose -f %COMPOSE_FILE% up -d
echo ✅ Services started!
echo.
echo Access URLs:
echo   🗄️  pgAdmin:     http://localhost:5050
echo   🪣  MinIO UI:    http://localhost:9001
echo   📊  Database:    localhost:5432
echo.
echo Next steps:
echo   1. Run 'dev-db.bat init-schema' to create database tables
echo   2. Run 'dev-db.bat test' to verify everything works
goto end

:stop_services
echo 🛑 Stopping development services...
docker-compose -f %COMPOSE_FILE% stop
echo ✅ Services stopped!
goto end

:restart_services
echo 🔄 Restarting development services...
docker-compose -f %COMPOSE_FILE% restart
echo ✅ Services restarted!
goto end

:reset_database
echo ⚠️  This will DELETE ALL DATABASE DATA!
set /p confirm=Are you sure? (y/N): 
if /I "%confirm%"=="y" (
    echo 🗑️  Resetting database...
    docker-compose -f %COMPOSE_FILE% down -v
    docker-compose -f %COMPOSE_FILE% up -d
    echo ✅ Database reset complete!
    echo Run 'dev-db.bat init-schema' to create tables
) else (
    echo ❌ Reset cancelled
)
goto end

:show_status
echo 📊 Service Status:
docker-compose -f %COMPOSE_FILE% ps
goto end

:show_logs
echo 📋 Service Logs:
docker-compose -f %COMPOSE_FILE% logs --tail=50
goto end

:connect_psql
echo 🔌 Connecting to PostgreSQL...
echo Database: marking_assistant
echo User: marking_user
echo.
docker exec -it postgres_dev psql -U marking_user -d marking_assistant
goto end

:init_schema
echo 🗃️  Initializing database schema...

if not exist "core" (
    echo ❌ Error: core directory not found
    echo Please run this script from the project root directory
    exit /b 1
)

rem Check if database is running
docker-compose -f %COMPOSE_FILE% ps | findstr "postgres_dev.*Up" >nul
if errorlevel 1 (
    echo Starting database first...
    docker-compose -f %COMPOSE_FILE% up -d postgres
    echo Waiting for database to be ready...
    timeout /t 5 /nobreak >nul
)

echo Creating database tables...
cd core
set ENV_FILE=../local.env
python -c "from configs.database import init_db; print('Initializing database schema...'); init_db(); print('✅ Database schema created successfully!')"
cd ..
echo ✅ Schema initialization complete!
goto end

:run_tests
echo 🧪 Running tests with database...

rem Check if database is running
docker-compose -f %COMPOSE_FILE% ps | findstr "postgres_dev.*Up" >nul
if errorlevel 1 (
    echo Starting database for tests...
    docker-compose -f %COMPOSE_FILE% up -d postgres
    timeout /t 5 /nobreak >nul
)

cd marking_assistant
python -m pytest tests/ -v
cd ..
goto end

:clean_all
echo ⚠️  This will remove ALL containers, volumes, and data!
set /p confirm=Are you sure? (y/N): 
if /I "%confirm%"=="y" (
    echo 🧹 Cleaning up...
    docker-compose -f %COMPOSE_FILE% down -v --remove-orphans
    docker system prune -f
    echo ✅ Cleanup complete!
) else (
    echo ❌ Cleanup cancelled
)
goto end

:unknown_command
echo ❌ Unknown command: %1
echo.
goto show_help

:end 