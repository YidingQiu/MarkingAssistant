-- Create read-only user for analytics/reporting
CREATE USER readonly_user WITH PASSWORD 'readonly_pass';

-- Grant connect privilege
GRANT CONNECT ON DATABASE marking_assistant TO readonly_user;

-- Grant usage on schema
GRANT USAGE ON SCHEMA public TO readonly_user;

-- Grant select on all tables (existing and future)
GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO readonly_user;

-- Grant select on all sequences (for accessing table metadata)
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO readonly_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO readonly_user;

-- Create extension if needed (for UUID generation)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Optional: Create any initial data or configuration tables here
-- (Tables will be created by SQLModel when the application starts) 