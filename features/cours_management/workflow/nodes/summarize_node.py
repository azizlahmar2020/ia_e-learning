from __future__ import annotations

import io
import logging
from PyPDF2 import PdfReader

from features.cours_management.agents.PDFInteractionAgent import PDFInteractionAgent
from ..graph_state import GraphState

logger = logging.getLogger(__name__)

pdf_agent = PDFInteractionAgent()


def _extract_text(pdf: bytes) -> str:
    try:
        with io.BytesIO(pdf) as buf:
            return "\n".join((p.extract_text() or "") for p in PdfReader(buf).pages)
    except Exception as e:
        logger.warning("PDF extraction failed: %s", e)
        return ""


def summarize_node(state: GraphState) -> GraphState:
    """Summarize uploaded PDF or text with memory context."""
    pdf = state.get("pdf_bytes")
    last = state["messages"][-1].content
    raw_text = _extract_text(pdf) if pdf else last

    result = pdf_agent.run(
        raw_text=raw_text,
        user_message=last,
        user_id=state.get("user_id"),
        conversation_id=state.get("conversation_id"),
    )

    state["result"] = {"response": result}
    return state
