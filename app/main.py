import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse

from app.chat import handle_chat
from app.models import ChatRequest, ChatResponse

logger = logging.getLogger("uvicorn.error")

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"

FRONTEND_ASSETS: dict[str, tuple[str, str]] = {
    "index.html": ("text/html; charset=utf-8", "no-cache"),
    "styles.css": ("text/css; charset=utf-8", "public, max-age=86400"),
    "app.js": ("application/javascript; charset=utf-8", "public, max-age=86400"),
}


@asynccontextmanager
async def lifespan(_: FastAPI):
    if FRONTEND_DIR.is_dir():
        logger.info("Serving frontend from %s", FRONTEND_DIR)
        for name in FRONTEND_ASSETS:
            if not (FRONTEND_DIR / name).is_file():
                logger.warning("Frontend asset missing at startup: %s", name)
    else:
        logger.warning("Frontend directory missing at startup: %s", FRONTEND_DIR)
    yield


app = FastAPI(title="Conversational SHL Assessment Recommender", lifespan=lifespan)


def frontend_file(name: str) -> Path:
    path = FRONTEND_DIR / name
    if not path.is_file():
        logger.error("Missing frontend asset: %s (looked in %s)", name, FRONTEND_DIR)
        raise HTTPException(status_code=404, detail=f"Frontend asset not found: {name}")
    return path


def frontend_response(name: str) -> FileResponse:
    media_type, cache_control = FRONTEND_ASSETS[name]
    return FileResponse(
        frontend_file(name),
        media_type=media_type,
        headers={"Cache-Control": cache_control},
    )


@app.get("/api")
def api_info() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "Conversational SHL Assessment Recommender",
        "endpoints": {
            "app": "/",
            "health": "/health",
            "chat": "/chat",
            "docs": "/docs",
        },
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return handle_chat(request)


@app.get("/app", include_in_schema=False)
@app.get("/app/", include_in_schema=False)
def legacy_app_path() -> RedirectResponse:
    return RedirectResponse(url="/", status_code=307)


@app.get("/", include_in_schema=False)
def serve_index() -> FileResponse:
    return frontend_response("index.html")


@app.get("/styles.css", include_in_schema=False)
def serve_styles() -> FileResponse:
    return frontend_response("styles.css")


@app.get("/app.js", include_in_schema=False)
def serve_app_js() -> FileResponse:
    return frontend_response("app.js")
