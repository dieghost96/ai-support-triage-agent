import json
import os
import time

from anthropic import AsyncAnthropic
from dotenv import load_dotenv
from langfuse import Langfuse
from langfuse.decorators import langfuse_context, observe

from app.models import FeedbackRequest, TicketRequest, TriageResult
from app.prompts import build_system_prompt, build_triage_prompt

load_dotenv()

_anthropic = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
_langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_BASE_URL", "http://localhost:3000"),
)

MODEL = "claude-sonnet-4-5"


class TriageError(Exception):
    pass


def _extract_json(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = text[3:]
        if text.startswith("json"):
            text = text[4:]
        end_fence = text.rfind("```")
        if end_fence != -1:
            text = text[:end_fence]
        text = text.strip()
    # Slice to outermost braces as a final safety net
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start : end + 1]
    return text


@observe(name="ticket-triage")
async def triage(ticket: TicketRequest) -> TriageResult:
    langfuse_context.update_current_trace(
        input={"ticket_id": ticket.ticket_id, "text": ticket.text},
    )
    try:
        parsed = await _run_triage_generation(ticket.text)
    except TriageError:
        raise
    except Exception as e:
        raise TriageError(f"Unexpected error during triage: {e}") from e

    trace_id = langfuse_context.get_current_trace_id()
    result = TriageResult(
        ticket_id=ticket.ticket_id,
        urgency=parsed["urgency"],
        category=parsed["category"],
        sentiment=parsed["sentiment"],
        automation_opportunity=parsed["automation_opportunity"],
        draft_response=parsed["draft_response"],
        confidence=parsed["confidence"],
        trace_id=trace_id,
    )
    langfuse_context.update_current_trace(output=result.model_dump())
    return result


@observe(name="triage-classification", as_type="generation")
async def _run_triage_generation(ticket_text: str) -> dict:
    messages = [{"role": "user", "content": build_triage_prompt(ticket_text)}]
    langfuse_context.update_current_observation(
        model=MODEL,
        input=messages,
        metadata={"system_prompt_version": "v1"},
    )

    t0 = time.monotonic()
    response = await _anthropic.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=build_system_prompt(),
        messages=messages,
    )
    latency_ms = round((time.monotonic() - t0) * 1000, 2)

    raw = response.content[0].text
    try:
        parsed = json.loads(_extract_json(raw))
    except json.JSONDecodeError as exc:
        langfuse_context.update_current_observation(
            output={"error": "invalid_json", "raw": raw[:500]},
        )
        raise TriageError(f"Model returned invalid JSON: {raw[:200]}") from exc

    langfuse_context.update_current_observation(
        output=parsed,
        usage={
            "input": response.usage.input_tokens,
            "output": response.usage.output_tokens,
        },
        metadata={"latency_ms": latency_ms},
    )
    return parsed


def submit_feedback(feedback: FeedbackRequest) -> None:
    _langfuse.score(
        trace_id=feedback.trace_id,
        name="user-feedback",
        value=feedback.score,
        comment=feedback.comment,
    )
