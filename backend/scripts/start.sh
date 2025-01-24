#!/bin/sh

# Function to check if PostgreSQL is ready
postgres_ready() {
    python << END
import sys
import asyncio
import asyncpg

async def check_db():
    try:
        conn = await asyncpg.connect(
            database="${POSTGRES_DB}",
            user="${POSTGRES_USER}",
            password="${POSTGRES_PASSWORD}",
            host="${POSTGRES_SERVER}"
        )
        await conn.close()
        return True
    except Exception:
        return False

if asyncio.run(check_db()):
    sys.exit(0)
sys.exit(-1)
END
}

# Wait for PostgreSQL to be ready
until postgres_ready; do
    >&2 echo "PostgreSQL is unavailable - sleeping"
    sleep 1
done

>&2 echo "PostgreSQL is up - executing command"

# Start the FastAPI application
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload 