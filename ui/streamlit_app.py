import os
import uuid

import httpx
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

st.set_page_config(
    page_title="AI Support Triage Agent",
    page_icon="🎫",
    layout="centered",
)

st.title("AI Support Triage Agent")
st.caption("Powered by Claude (claude-sonnet-4-5) · Traced by Langfuse")

if "last_result" not in st.session_state:
    st.session_state["last_result"] = None
if "feedback_submitted" not in st.session_state:
    st.session_state["feedback_submitted"] = False

# --- Input ---
with st.form("triage_form"):
    ticket_id = st.text_input(
        "Ticket ID",
        value=f"TKT-{uuid.uuid4().hex[:6].upper()}",
        help="Auto-generated — edit freely.",
    )
    ticket_text = st.text_area(
        "Customer Message",
        placeholder="Paste or type the customer's support message here...",
        height=160,
    )
    submitted = st.form_submit_button(
        "Analyze Ticket", use_container_width=True, type="primary"
    )

if submitted:
    if not ticket_text.strip():
        st.warning("Please enter a support message before analyzing.")
        st.stop()

    st.session_state["feedback_submitted"] = False
    with st.spinner("Analyzing with Claude..."):
        try:
            resp = httpx.post(
                f"{API_BASE_URL}/triage",
                json={"ticket_id": ticket_id, "text": ticket_text},
                timeout=30.0,
            )
            resp.raise_for_status()
            st.session_state["last_result"] = resp.json()
        except httpx.HTTPStatusError as e:
            st.error(f"API error {e.response.status_code}: {e.response.text}")
            st.stop()
        except httpx.RequestError as e:
            st.error(f"Could not reach the API at {API_BASE_URL}: {e}")
            st.stop()

# --- Results ---
result = st.session_state["last_result"]
if result:
    st.divider()
    st.subheader("Triage Result")

    urgency_label = {"high": "🔴 HIGH", "medium": "🟡 MEDIUM", "low": "🟢 LOW"}.get(
        result["urgency"], result["urgency"].upper()
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Urgency", urgency_label)
    c2.metric("Category", result["category"].capitalize())
    c3.metric("Sentiment", result["sentiment"].capitalize())

    c4, c5 = st.columns(2)
    c4.metric("Confidence", f"{result['confidence']:.0%}")
    c5.metric(
        "Automation Opportunity",
        "Yes ✅" if result["automation_opportunity"] else "No ❌",
    )

    st.subheader("Draft Response")
    st.info(result["draft_response"])
    st.caption(f"Trace ID: `{result['trace_id']}`")

    # --- Feedback ---
    st.divider()
    if st.session_state["feedback_submitted"]:
        st.success("Feedback submitted — thank you!")
    else:
        st.subheader("Rate this triage")
        st.caption("1 = Poor  ·  5 = Excellent")
        cols = st.columns(5)
        for i, col in enumerate(cols, start=1):
            if col.button(
                "⭐" * i,
                key=f"fb_{i}",
                use_container_width=True,
                help=f"{i} star{'s' if i > 1 else ''}",
            ):
                try:
                    fb = httpx.post(
                        f"{API_BASE_URL}/feedback",
                        json={
                            "trace_id": result["trace_id"],
                            "score": round(i / 5.0, 2),
                        },
                        timeout=10.0,
                    )
                    fb.raise_for_status()
                    st.session_state["feedback_submitted"] = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Feedback failed: {e}")
