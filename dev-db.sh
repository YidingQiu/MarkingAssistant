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
    echo ""
    echo "Service URLs:"
    echo "  PostgreSQL:  localhost:5432"
    echo "  MinIO API:   http://localhost:9000"
    echo "  MinIO UI:    http://localhost:9001"
    echo "  pgAdmin:     http://localhost:5050"
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
    echo "  📊  Database:    localhost:5432"
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
    export ENV_FILE=../local.env
    python -c "
from configs.database import init_db
print('Initializing database schema...')
init_db()
print('✅ Database schema created successfully!')
"
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