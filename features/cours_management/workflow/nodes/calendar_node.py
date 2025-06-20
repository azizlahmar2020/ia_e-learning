from __future__ import annotations

from features.cours_management.agents.schedule_agent import ScheduleAgent
from ..graph_state import GraphState

schedule_agent = ScheduleAgent()


def calendar_node(state: GraphState) -> GraphState:
    last = state["messages"][-1].content
    result = schedule_agent.handle(last)
    state["result"] = result
    return state
