from fastapi import FastAPI

from app.chat import handle_chat
from app.models import ChatRequest, ChatResponse

app = FastAPI(title="Conversational SHL Assessment Recommender")


@app.get("/")
def root() -> dict[str, object]:
    return {
        "status": "ok",
        "service": "Conversational SHL Assessment Recommender",
        "endpoints": {
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
