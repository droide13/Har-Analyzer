"""FastAPI app entrypoint. Run with: uvicorn app.main:app --reload"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.har import router as har_router

app = FastAPI(title="HAR Analyzer API", version="0.1.0")

# Local, single-user dev tool: the frontend (Vite dev server) runs on a
# different port than the API, so CORS needs to be open between the two.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(har_router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}
