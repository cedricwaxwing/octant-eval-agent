from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from agent import answer_question, load_dataset


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    model: Optional[str] = None
    epochs: List[int] = []


app = FastAPI(title="Octant Eval Agent API")

DATASET: Dict[str, Any] = load_dataset()
META = DATASET.get("meta", {})
EPOCH_KEYS = sorted(int(e) for e in DATASET.get("epochs", {}).keys())


@app.get("/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "current_epoch": META.get("current_epoch"),
        "epoch_count": len(EPOCH_KEYS),
    }


@app.get("/epochs")
def epochs() -> Dict[str, Any]:
    return {
        "epochs": EPOCH_KEYS,
        "current_epoch": META.get("current_epoch"),
    }


@app.post("/ask", response_model=AskResponse)
def ask(body: AskRequest) -> AskResponse:
    # For now we only return the answer and basic metadata;
    # more detailed context (projects, allocations) can be added later.
    answer = answer_question(body.question, DATASET)
    from agent import os as _os  # type: ignore

    model = _os.getenv("ANTHROPIC_MODEL")
    return AskResponse(answer=answer, model=model, epochs=EPOCH_KEYS)

