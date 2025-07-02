from __future__ import annotations

from typing import Annotated
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_groq import ChatGroq


class GraphState(TypedDict):
    """State tracked by the basic chatbot graph."""

    messages: Annotated[list, add_messages]


graph_builder = StateGraph(GraphState)

llm = ChatGroq(model_name="llama3-8b-8192", temperature=0)


def chatbot(state: GraphState) -> dict:
    """Simple chatbot node returning the model response."""
    return {"messages": [llm.invoke(state["messages"])]}


graph_builder.add_node("chatbot", chatbot)

# Entry and exit points
graph_builder.add_edge(START, "chatbot")
graph_builder.add_edge("chatbot", END)

workflow = graph_builder.compile()
