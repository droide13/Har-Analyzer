"""FastAPI app entrypoint.

Dev: uvicorn app.main:app --reload
Prod: build the frontend first (cd frontend && npm run build), then
uvicorn app.main:app --host 0.0.0.0 --port 8000 (no --reload) -- see
readme.md's Deployment section.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers.cookies import router as cookies_router
from app.routers.dissemination import router as dissemination_router
from app.routers.har import router as har_router
from app.routers.identifiers import router as identifiers_router
from app.routers.metadata import router as metadata_router
from app.routers.naming import router as naming_router
from app.routers.overview import router as overview_router
from app.routers.query_params import router as query_params_router

app = FastAPI(title="HAR Analyzer API", version="0.1.0")

# Local, single-user dev tool: the frontend (Vite dev server) runs on a
# different port than the API, so CORS needs to be open between the two.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

for router in (
    har_router,
    overview_router,
    cookies_router,
    query_params_router,
    identifiers_router,
    dissemination_router,
    metadata_router,
    naming_router,
):
    app.include_router(router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    """Liveness check."""
    return {"status": "ok"}


# Serves the built frontend (frontend/dist/, produced by `npm run build`) on
# this same origin/port -- only if it's actually been built. frontend/dist/
# is gitignored and never exists in local dev (dev.sh runs the Vite dev
# server separately instead), so this is a no-op there and only activates
# once a built frontend has been deployed alongside it. Mounted last so the
# API routers above always get first try at matching a request.
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
