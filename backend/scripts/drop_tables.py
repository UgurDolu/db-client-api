from sqlalchemy import create_engine, text

# Database connection
engine = create_engine("postgresql://postgres:postgres@localhost/db_client")

# Drop all tables and types
with engine.connect() as connection:
    connection.execute(text("DROP TABLE IF EXISTS queries, user_settings, users CASCADE"))
    connection.execute(text("DROP TYPE IF EXISTS querystatus"))
    connection.commit() 