"""
Simple FastAPI server for Verus Lemma Finder web demo.

Usage:
    uv run fastapi dev demo/server.py
"""

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from verus_lemma_finder.models import LemmaInfo
from verus_lemma_finder.search import LemmaSearcher

# ==================== Data Models ====================

class SearchRequest(BaseModel):
    query: str
    top_k: int = 10
    project: str = "dalek"  # "dalek" or future projects

class SearchResult(BaseModel):
    name: str
    file_path: str
    line_number: Optional[int]
    documentation: str
    signature: str
    requires_clauses: List[str]
    ensures_clauses: List[str]
    score: float
    source: str
    github_url: Optional[str] = None

class SearchResponse(BaseModel):
    results: List[SearchResult]
    query: str
    total: int
    search_method: str

# Global searcher instances (loaded on startup)
searchers = {}

# GitHub repository mappings
GITHUB_REPOS = {
    "dalek": {
        "url": "https://github.com/verus-lang/verus",
        "branch": "main",
        "index_file": "data/curve25519-dalek_lemma_index.json"
    }
}

# ==================== Lifespan Management ====================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load indexes on startup, cleanup on shutdown."""
    print("🚀 Loading indexes...")
    
    project_root = Path(__file__).parent.parent
    
    for project_name, config in GITHUB_REPOS.items():
        index_file = project_root / config["index_file"]
        
        if index_file.exists():
            try:
                searchers[project_name] = LemmaSearcher(
                    index_file=index_file,
                    use_embeddings=True  # Full semantic search!
                )
                print(f"✓ Loaded {project_name} index")
            except Exception as e:
                print(f"⚠️  Failed to load {project_name}: {e}")
        else:
            print(f"⚠️  Index not found for {project_name}: {index_file}")
    
    if not searchers:
        print("⚠️  WARNING: No indexes loaded! Demo won't work properly.")
    else:
        print(f"✓ Ready with {len(searchers)} project(s)")
    
    yield  # Server runs
    
    # Cleanup on shutdown (if needed)
    print("Shutting down...")

# ==================== App Setup ====================

app = FastAPI(
    title="Verus Lemma Finder API",
    description="Search for Verus lemmas and specifications",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for all origins (for demo purposes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== API Endpoints ====================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the demo HTML page."""
    html_file = Path(__file__).parent / "index.html"
    if html_file.exists():
        return HTMLResponse(content=html_file.read_text())
    return HTMLResponse("<h1>Verus Lemma Finder Demo</h1><p>index.html not found</p>")

@app.get("/api/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "projects": list(searchers.keys()),
        "total_lemmas": {
            project: len(searcher.lemmas)
            for project, searcher in searchers.items()
        }
    }

@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest):
    """
    Search for lemmas in the specified project.
    
    Returns top-k results with relevance scores.
    """
    if request.project not in searchers:
        raise HTTPException(
            status_code=404, 
            detail=f"Project '{request.project}' not found. Available: {list(searchers.keys())}"
        )
    
    searcher = searchers[request.project]
    
    # Perform search
    results = searcher.search(request.query, top_k=request.top_k)
    
    # Determine search method used
    search_method = "semantic+keyword" if searcher.embeddings is not None else "keyword"
    
    # Convert to response format with GitHub URLs
    github_config = GITHUB_REPOS[request.project]
    search_results = []
    
    for lemma, score in results:
        # Generate GitHub URL
        github_url = None
        if lemma.file_path and lemma.line_number:
            github_url = (
                f"{github_config['url']}/blob/{github_config['branch']}/"
                f"{lemma.file_path}#L{lemma.line_number}"
            )
        
        search_results.append(
            SearchResult(
                name=lemma.name,
                file_path=lemma.file_path,
                line_number=lemma.line_number,
                documentation=lemma.documentation,
                signature=lemma.signature,
                requires_clauses=lemma.requires_clauses,
                ensures_clauses=lemma.ensures_clauses,
                score=score,
                source=lemma.source,
                github_url=github_url
            )
        )
    
    return SearchResponse(
        results=search_results,
        query=request.query,
        total=len(search_results),
        search_method=search_method
    )

@app.get("/api/projects")
async def list_projects():
    """List available projects for searching."""
    return {
        "projects": [
            {
                "name": project,
                "github_url": config["url"],
                "lemma_count": len(searchers[project].lemmas) if project in searchers else 0,
                "has_embeddings": searchers[project].embeddings is not None if project in searchers else False
            }
            for project, config in GITHUB_REPOS.items()
        ]
    }

# ==================== Run Instructions ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

