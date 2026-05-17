from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.chat import handle_chat
from app.models import ChatRequest, ChatResponse

app = FastAPI(title="Conversational SHL Assessment Recommender")

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


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


if FRONTEND_DIR.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
