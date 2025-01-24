import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.endpoints import auth, users, queries
from app.services.query_listener import query_listener
import asyncio

app = FastAPI(
    title="DB Client API",
    description="A powerful and flexible Database Client API for handling database queries asynchronously",
    version="1.0.0"
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(queries.router, prefix="/api/queries", tags=["Queries"])

@app.on_event("startup")
async def startup_event():
    # Start query listener in the background
    asyncio.create_task(query_listener.start())

@app.on_event("shutdown")
async def shutdown_event():
    # Stop query listener
    await query_listener.stop()

@app.get("/")
async def root():
    return {"message": "Welcome to DB Client API"}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app"]
    ) 