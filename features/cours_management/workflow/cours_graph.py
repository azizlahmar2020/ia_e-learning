from __future__ import annotations

from langgraph.graph import StateGraph, END

from .graph_state import GraphState
from .nodes.detect_operations import detect_operations
from .nodes.summarize_node import summarize_node
from .nodes.process_pdf_node import process_pdf_node
from .nodes.chat_node import chat_node
from .nodes.quiz_node import quiz_node
from .nodes.calendar_node import calendar_node
from .nodes.user_crud_node import user_crud_node
from .nodes.save_node import save_node


builder = StateGraph(GraphState)

builder.set_entry_point("detect_operations")

builder.add_node("detect_operations", detect_operations)
builder.add_node("summarize_node", summarize_node)
builder.add_node("process_pdf_node", process_pdf_node)
builder.add_node("chat_node", chat_node)
builder.add_node("quiz_node", quiz_node)
builder.add_node("calendar_node", calendar_node)
builder.add_node("user_crud_node", user_crud_node)
builder.add_node("save_node", save_node)


def route(state: GraphState) -> str:
    return state.get("operation") or "chat"

builder.add_conditional_edges(
    "detect_operations",
    condition=route,
    path_map={
        "summarize": "summarize_node",
        "process_pdf": "process_pdf_node",
        "chat": "chat_node",
        "quiz": "quiz_node",
        "show_calendar": "calendar_node",
        "schedule_session": "calendar_node",
        "user": "user_crud_node",
        "course": "chat_node",
    },
)

for node in [
    "summarize_node",
    "process_pdf_node",
    "chat_node",
    "quiz_node",
    "calendar_node",
    "user_crud_node",
]:
    builder.add_edge(node, "save_node")

builder.add_edge("save_node", END)

workflow = builder.compile()
