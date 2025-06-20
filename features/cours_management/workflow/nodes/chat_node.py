from __future__ import annotations

from langchain_core.messages import AIMessage

from features.chatbot.tools.chatbot_tools import ChatbotTools
from ..graph_state import GraphState

chat_tools = ChatbotTools()


def chat_node(state: GraphState) -> GraphState:
    """Default chat behaviour using ChatbotTools."""
    last = state["messages"][-1].content
    history_text = "\n".join(state.get("history") or [])
    input_data = {"input": last, "history": history_text}
    if state.get("rag_context"):
        input_data["history"] += "\n" + state["rag_context"]

    response = chat_tools.chat_tool.invoke(input_data)
    state["result"] = {"response": response}
    state["messages"].append(AIMessage(content=response))
    return state
