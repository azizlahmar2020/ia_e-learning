from __future__ import annotations

import io
import logging
from typing import List
from langchain_core.messages import SystemMessage
from PyPDF2 import PdfReader

from features.cours_management.agents.OperationDetectionAgent import OperationDetectionAgent
from features.cours_management.agents.rag_agent import RAGAgent
from features.cours_management.memory_course.conversation_memory import ConversationMemory
from ..graph_state import GraphState

logger = logging.getLogger(__name__)

conversation_memory = ConversationMemory()
router = OperationDetectionAgent()
rag_agent = RAGAgent()

_MAX_CONTEXT = 3000
_MAX_HISTORY = 10


def _extract_text(pdf: bytes) -> str:
    try:
        with io.BytesIO(pdf) as buf:
            return "\n".join((page.extract_text() or "") for page in PdfReader(buf).pages)
    except Exception as e:
        logger.warning("PDF extraction failed: %s", e)
        return ""


def truncate(text: str, n: int = _MAX_CONTEXT) -> str:
    return text if len(text) <= n else text[:n] + "…"


def detect_operations(state: GraphState) -> GraphState:
    """Detect the next operation from user input and enrich context."""
    user_msg = state["messages"][-1].content
    role = (state.get("user_role") or "public").lower()
    user_id = state.get("user_id") or ""
    conv_id = state["conversation_id"]
    pdf = state.get("pdf_bytes")

    # Fetch conversation history
    raw_history = conversation_memory.get_recent_conversations(user_id, conv_id, _MAX_HISTORY)
    history_msgs = ConversationMemory.reconstruct_messages(raw_history, _MAX_CONTEXT)
    history_lines: List[str] = []
    hist_text = ""
    for msg in history_msgs:
        line = f"{msg.type.capitalize()}: {msg.content}"
        history_lines.append(line)
        hist_text += line + "\n"
    state["history"] = history_lines

    # Retrieve RAG context
    rag_ctx = ""
    try:
        rag_data = rag_agent.process_query(user_msg, hist_text)
        rag_ctx = rag_data.get("enriched_context", "")
    except Exception as e:
        logger.warning("RAG retrieval failed: %s", e)
    state["rag_context"] = rag_ctx

    # Build system prompt
    intro = f"Historique recent:\n{hist_text}\n{rag_ctx}".strip()
    state["messages"].insert(0, SystemMessage(content=truncate(intro)))

    # Detect operation
    label = router.detect_category(user_msg, role, bool(pdf), history=hist_text)
    state["operation"] = label or "chat"
    return state
