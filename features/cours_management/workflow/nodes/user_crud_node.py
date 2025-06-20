from __future__ import annotations

from features.user_management.agents.user_agent import UserAgent
from features.user_management.tools.user_tools import UserTools
from ..graph_state import GraphState

user_agent = UserAgent()


def user_crud_node(state: GraphState) -> GraphState:
    last = state["messages"][-1].content
    op_data = user_agent.detect_operation(last)
    name = op_data.get("operation")
    params = op_data.get("parameters", {}) or {}

    tools = UserTools(state.get("user_role", "Public"))
    tool = getattr(tools, name, None)
    if tool:
        result = tool.invoke(params)
    else:
        result = {"error": f"Unknown operation: {name}"}

    state["result"] = result
    return state
