#!/bin/bash

# Development Database Management Script
# Usage: ./dev-db.sh [command]

set -e

COMPOSE_FILE="docker-compose.dev.yml"

show_help() {
    echo "Development Database Management Script"
    echo ""
    echo "Usage: ./dev-db.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start       - Start all development services"
    echo "  stop        - Stop all development services"
    echo "  restart     - Restart all development services"
    echo "  reset       - Reset database (removes all data)"
    echo "  status      - Show status of all services"
    echo "  logs        - Show logs from all services"
    echo "  psql        - Connect to PostgreSQL database"
    echo "  init-schema - Initialize database schema (run core app)"
    echo "  test        - Run tests with database"
    echo "  clean       - Remove all containers and volumes"
    echo "  redis       - Connect to Redis CLI"
    echo "  celery      - Start Celery worker locally"
    echo "  flower      - Start Flower monitoring locally"
    echo "  test-celery - Test Celery setup"
    echo ""
    echo "Service URLs:"
    echo "  PostgreSQL:  localhost:15432"
    echo "  MinIO API:   http://localhost:9000"
    echo "  MinIO UI:    http://localhost:9001"
    echo "  pgAdmin:     http://localhost:5050"
    echo "  Redis:       localhost:6379"
    echo "  Flower:      http://localhost:5555 (when enabled)"
    echo "  Core API:    http://localhost:8000"
}

start_services() {
    echo "🚀 Starting development services..."
    docker-compose -f $COMPOSE_FILE up -d
    echo "✅ Services started!"
    echo ""
    echo "Access URLs:"
    echo "  🗄️  pgAdmin:     http://localhost:5050"
    echo "  🪣  MinIO UI:    http://localhost:9001" 
    echo "  📊  Database:    localhost:15432"
    echo "  🔴  Redis:       localhost:6379"
    echo ""
    echo "Next steps:"
    echo "  1. Run './dev-db.sh init-schema' to create database tables"
    echo "  2. Run './dev-db.sh test' to verify everything works"
}

stop_services() {
    echo "🛑 Stopping development services..."
    docker-compose -f $COMPOSE_FILE stop
    echo "✅ Services stopped!"
}

restart_services() {
    echo "🔄 Restarting development services..."
    docker-compose -f $COMPOSE_FILE restart
    echo "✅ Services restarted!"
}

reset_database() {
    echo "⚠️  This will DELETE ALL DATABASE DATA!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🗑️  Resetting database..."
        docker-compose -f $COMPOSE_FILE down -v
        docker-compose -f $COMPOSE_FILE up -d
        echo "✅ Database reset complete!"
        echo "Run './dev-db.sh init-schema' to create tables"
    else
        echo "❌ Reset cancelled"
    fi
}

show_status() {
    echo "📊 Service Status:"
    docker-compose -f $COMPOSE_FILE ps
}

show_logs() {
    echo "📋 Service Logs:"
    docker-compose -f $COMPOSE_FILE logs --tail=50
}

connect_psql() {
    echo "🔌 Connecting to PostgreSQL..."
    echo "Database: marking_assistant"
    echo "User: marking_user"
    echo ""
    docker exec -it postgres_dev psql -U marking_user -d marking_assistant
}

init_schema() {
    echo "🗃️  Initializing database schema..."
    
    # Check if core directory exists
    if [ ! -d "core" ]; then
        echo "❌ Error: core directory not found"
        echo "Please run this script from the project root directory"
        exit 1
    fi
    
    # Start database if not running
    if ! docker-compose -f $COMPOSE_FILE ps | grep -q "postgres_dev.*Up"; then
        echo "Starting database first..."
        docker-compose -f $COMPOSE_FILE up -d postgres
        echo "Waiting for database to be ready..."
        sleep 5
    fi
    
    echo "Creating database tables..."
    cd core
    python init_db.py
    cd ..
    echo "✅ Schema initialization complete!"
}

run_tests() {
    echo "🧪 Running tests with database..."
    
    # Start database if not running
    if ! docker-compose -f $COMPOSE_FILE ps | grep -q "postgres_dev.*Up"; then
        echo "Starting database for tests..."
        docker-compose -f $COMPOSE_FILE up -d postgres
        sleep 5
    fi
    
    cd marking_assistant
    python -m pytest tests/ -v
    cd ..
}

clean_all() {
    echo "⚠️  This will remove ALL containers, volumes, and data!"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🧹 Cleaning up..."
        docker-compose -f $COMPOSE_FILE down -v --remove-orphans
        docker system prune -f
        echo "✅ Cleanup complete!"
    else
        echo "❌ Cleanup cancelled"
    fi
}

connect_redis() {
    echo "🔌 Connecting to Redis..."
    docker exec -it redis_dev redis-cli
}

start_celery_worker() {
    echo "🔧 Starting Celery worker locally..."
    echo "Make sure Redis is running first!"
    echo ""
    
    # Check if redis is running
    if ! docker-compose -f $COMPOSE_FILE ps | grep -q "redis_dev.*Up"; then
        echo "Starting Redis first..."
        docker-compose -f $COMPOSE_FILE up -d redis
        echo "Waiting for Redis to be ready..."
        sleep 3
    fi
    
    echo "Starting Celery worker..."
    celery -A worker worker --pool=solo --loglevel=info --queues=default --concurrency=1
}

start_flower() {
    echo "🌸 Starting Flower monitoring locally..."
    echo "Make sure Redis is running first!"
    echo ""
    
    # Check if redis is running
    if ! docker-compose -f $COMPOSE_FILE ps | grep -q "redis_dev.*Up"; then
        echo "Starting Redis first..."
        docker-compose -f $COMPOSE_FILE up -d redis
        echo "Waiting for Redis to be ready..."
        sleep 3
    fi
    
    echo "Starting Flower on http://localhost:5555"
    celery -A worker flower --port=5555
}

test_celery() {
    echo "🧪 Testing Celery setup..."
    
    # Check if redis is running
    if ! docker-compose -f $COMPOSE_FILE ps | grep -q "redis_dev.*Up"; then
        echo "Starting Redis for test..."
        docker-compose -f $COMPOSE_FILE up -d redis
        echo "Waiting for Redis to be ready..."
        sleep 3
    fi
    
    echo "Testing Celery task execution..."
    python -c "
from worker import app
from core.celery.tasks.hello import hello_world
import sys
try:
    print('Testing task registration...')
    result = hello_world.delay('Celery Test')
    print(f'Task started with ID: {result.id}')
    print('✅ Celery task queued successfully!')
    print(f'Check task status via API: curl -X GET \"http://localhost:8000/celery/status/{result.id}\"')
except Exception as e:
    print(f'❌ Celery test failed: {e}')
    sys.exit(1)
"
}

# Main command handling
case "${1:-help}" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    reset)
        reset_database
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    psql)
        connect_psql
        ;;
    init-schema)
        init_schema
        ;;
    test)
        run_tests
        ;;
    clean)
        clean_all
        ;;
    redis)
        connect_redis
        ;;
    celery)
        start_celery_worker
        ;;
    flower)
        start_flower
        ;;
    test-celery)
        test_celery
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "❌ Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac 