from __future__ import annotations

import logging

from features.cours_management.agents.cours_agent import CourseAgent
from ..graph_state import GraphState

logger = logging.getLogger(__name__)

course_agent = CourseAgent()


def process_pdf_node(state: GraphState) -> GraphState:
    pdf = state.get("pdf_bytes")
    if not pdf:
        state["result"] = {"error": "No PDF provided."}
        return state

    try:
        result = course_agent.process_pdf(pdf)
        state["result"] = result
    except Exception as e:
        logger.error("PDF processing failed: %s", e)
        state["result"] = {"error": str(e)}
    return state
