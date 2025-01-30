import os
import sys
import uvicorn
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add the backend directory to the Python path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Now we can import our modules
from app.core.config import settings
from app.api.api_v1.api import api_router
from app.db.session import engine, dispose_engine
from app.db.base import Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        logger.info("Starting up application...")
        logger.info("Creating database tables...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")
        yield
    except Exception as e:
        logger.error(f"Error during startup: {str(e)}")
        raise
    finally:
        # Shutdown
        logger.info("Shutting down application...")
        await dispose_engine()
        logger.info("Application shutdown complete")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    version="1.0.0",
    lifespan=lifespan
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount static files
app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")

@app.get("/")
async def root():
    return FileResponse("static/index.html")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    # Serve API documentation
    if full_path == "docs" or full_path == "redoc":
        raise HTTPException(status_code=404)
    
    # For all other paths, serve the SPA index.html
    return FileResponse("static/index.html")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 