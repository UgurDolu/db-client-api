-- Create the QueryStatus enum type
CREATE TYPE query_status AS ENUM ('pending', 'queued', 'running', 'completed', 'failed');

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
    status query_status NOT NULL DEFAULT 'pending',
    export_location VARCHAR(255),
    export_type VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
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
    IF NEW.status = 'running' AND OLD.status != 'running' THEN
        NEW.started_at = CURRENT_TIMESTAMP;
    ELSIF NEW.status IN ('completed', 'failed') AND OLD.status NOT IN ('completed', 'failed') THEN
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