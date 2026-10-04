"""Main FastAPI application entrypoint for Study Buddy."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment configuration from .env
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.routes.documents import router as documents_router
from app.routes.chat import router as chat_router

app = FastAPI(
    title="Study Buddy API",
    description="A lightweight AI-powered study assistant for querying uploaded documents.",
    version="0.2.0",
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(documents_router)
app.include_router(chat_router)

# Mount static frontend
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", tags=["frontend"], summary="Study Buddy Web Interface")
async def serve_frontend():
    """Serve the Study Buddy single-page web interface."""
    index_file = STATIC_DIR / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)
    return {
        "message": "Study Buddy API is running. Visit /docs for API documentation.",
        "version": "0.2.0",
    }


@app.get("/health", tags=["health"], summary="Health Check")
async def health_check():
    """Health check endpoint to verify server status."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))

    uvicorn.run("app.main:app", host=host, port=port, reload=True)
