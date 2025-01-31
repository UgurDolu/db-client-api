\c dbclient

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create the schema
CREATE SCHEMA IF NOT EXISTS public;

-- Set default privileges
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO postgres;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO postgres;

-- Drop existing enum type if exists
DROP TYPE IF EXISTS query_status CASCADE;

-- Create the QueryStatus enum type
CREATE TYPE query_status AS ENUM ('pending', 'queued', 'running', 'transferring', 'completed', 'failed');

-- Create function to compare query_status with text
CREATE OR REPLACE FUNCTION compare_query_status(query_status, text)
RETURNS boolean AS $$
BEGIN
    RETURN $1::text = $2;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Create operator for comparison
CREATE OPERATOR = (
    LEFTARG = query_status,
    RIGHTARG = text,
    PROCEDURE = compare_query_status,
    COMMUTATOR = =
);

-- Create users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX ix_users_id ON users(id);
CREATE INDEX ix_users_email ON users(email);

-- Create user_settings table
CREATE TABLE user_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    export_location VARCHAR(255),
    export_type VARCHAR(50),
    max_parallel_queries INTEGER DEFAULT 3,
    ssh_hostname VARCHAR(255),
    ssh_port INTEGER DEFAULT 22,
    ssh_username VARCHAR(255),
    ssh_password VARCHAR(255),
    ssh_key TEXT,
    ssh_key_passphrase VARCHAR(255),
    CONSTRAINT fk_user_settings_user FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX ix_user_settings_id ON user_settings(id);
CREATE INDEX ix_user_settings_user_id ON user_settings(user_id);

-- Create queries table
CREATE TABLE queries (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    db_username VARCHAR(255) NOT NULL,
    db_password VARCHAR(255) NOT NULL,
    db_tns VARCHAR(255) NOT NULL,
    query_text TEXT NOT NULL,
    status query_status NOT NULL DEFAULT 'pending'::query_status,
    export_location VARCHAR(255),
    export_type VARCHAR(50),
    export_filename VARCHAR(255),
    ssh_hostname VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    result_metadata JSONB,
    CONSTRAINT fk_queries_user FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX ix_queries_id ON queries(id);
CREATE INDEX ix_queries_user_id ON queries(user_id);
CREATE INDEX ix_queries_status ON queries(status);
CREATE INDEX ix_queries_created_at ON queries(created_at DESC);

-- Create function to automatically update timestamps
CREATE OR REPLACE FUNCTION update_query_timestamps()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    IF NEW.status = 'running'::query_status AND OLD.status != 'running'::query_status THEN
        NEW.started_at = CURRENT_TIMESTAMP;
    ELSIF NEW.status IN ('completed'::query_status, 'failed'::query_status) 
          AND OLD.status NOT IN ('completed'::query_status, 'failed'::query_status) THEN
        NEW.completed_at = CURRENT_TIMESTAMP;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for automatic timestamp updates
CREATE TRIGGER update_query_timestamps_trigger
    BEFORE UPDATE ON queries
    FOR EACH ROW
    EXECUTE FUNCTION update_query_timestamps(); 