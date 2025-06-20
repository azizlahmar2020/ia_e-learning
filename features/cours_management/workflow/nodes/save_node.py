from __future__ import annotations

from langchain_core.messages import BaseMessage, HumanMessage

from features.cours_management.memory_course.conversation_memory import ConversationMemory
from ..graph_state import GraphState

conversation_memory = ConversationMemory()


def save_node(state: GraphState) -> GraphState:
    """Save the last user/assistant exchange to conversation memory."""
    user_id = state.get("user_id") or ""
    conv_id = state.get("conversation_id")

    user_msg = ""
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            user_msg = msg.content
            break

    assistant_msg = ""
    if isinstance(state.get("result"), dict) and "response" in state["result"]:
        assistant_msg = str(state["result"]["response"])
    elif state.get("result") is not None:
        assistant_msg = str(state["result"])

    if user_msg or assistant_msg:
        conversation_memory.save_conversation(
            user_id=user_id,
            conversation_id=conv_id,
            user_message=user_msg,
            assistant_message=assistant_msg,
            meta={"operation": state.get("operation") or ""},
        )
    return state
