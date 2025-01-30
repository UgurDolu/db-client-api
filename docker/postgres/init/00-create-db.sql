-- Create the database if it doesn't exist
SELECT 'CREATE DATABASE dbclient'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'dbclient')\gexec 