from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.agent import TriageError, submit_feedback, triage
from app.models import FeedbackRequest, TicketRequest, TriageResult


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="AI Support Triage Agent",
    description="Classifies support tickets and generates draft responses using Claude.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/triage", response_model=TriageResult)
async def triage_ticket(ticket: TicketRequest) -> TriageResult:
    try:
        return await triage(ticket)
    except TriageError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/feedback", status_code=204)
async def feedback(request: FeedbackRequest) -> None:
    try:
        submit_feedback(request)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to submit feedback: {e}")
