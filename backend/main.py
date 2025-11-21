"""FastAPI main application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .database import init_database
from .api import projects, chat, papers, documents, files, stats


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    init_database()
    yield
    # Shutdown
    pass


app = FastAPI(
    title="Paper Agent API",
    description="医学研究者向け論文管理・文書作成AIエージェント",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router, prefix="/api/projects", tags=["Projects"])
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])
app.include_router(papers.router, prefix="/api/papers", tags=["Papers"])
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(files.router, prefix="/api/files", tags=["Files"])
app.include_router(stats.router, prefix="/api/stats", tags=["Stats"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Paper Agent API", "version": "0.1.0"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
