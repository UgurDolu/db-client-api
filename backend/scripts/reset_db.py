from sqlalchemy import create_engine, text

# Database connection to postgres database
engine = create_engine("postgresql://postgres:postgres@localhost/postgres")

# Drop and recreate the database
with engine.connect() as connection:
    connection.execute(text("COMMIT"))  # Close any open transactions
    
    # Terminate all connections to the database
    connection.execute(text("""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = 'db_client'
        AND pid <> pg_backend_pid()
    """))
    
    # Drop and recreate the database using template0
    connection.execute(text("DROP DATABASE IF EXISTS db_client"))
    connection.execute(text("CREATE DATABASE db_client TEMPLATE template0"))
    print("Database reset completed.") 