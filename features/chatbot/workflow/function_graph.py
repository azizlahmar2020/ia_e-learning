from __future__ import annotations

import operator
from typing import List, TypedDict, Annotated

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_groq import ChatGroq
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.tools import Tool

from features.chatbot.tools.chatbot_tools import ChatbotTools
from features.cours_management.tools.cours_tools import CourseTools
from features.user_management.tools.user_tools import UserTools


class GraphState(TypedDict):
    """State tracked by the tool calling graph."""

    messages: Annotated[List[HumanMessage], operator.add]
    results: List[str]
    error: str | None


# Initialise tools -------------------------------------------------------------
chat_tools = ChatbotTools()
course_tools = CourseTools()
user_tools = UserTools(user_role="Admin")

TOOLS = [
    chat_tools.chat_tool,
    Tool.from_function(
        chat_tools.get_date,
        name="get_date",
        description="Return today's date in ISO format",
    ),
    Tool.from_function(
        chat_tools.get_time,
        name="get_time",
        description="Return the current time in ISO format",
    ),
    CourseTools.get_courses,
    CourseTools.get_course_by_id,
    UserTools.get_users,
    UserTools.get_user_by_id,
    UserTools.create_user,
    UserTools.update_user,
    UserTools.delete_user,
]


# LLM + agent -----------------------------------------------------------------
llm = ChatGroq(model_name="llama3-8b-8192", temperature=0)
agent = create_openai_functions_agent(llm, TOOLS)
executor = AgentExecutor(agent=agent, tools=TOOLS, verbose=True)


# Step function ---------------------------------------------------------------
def agent_step(state: GraphState) -> GraphState:
    """Run the OpenAI functions agent and append its response."""

    last = state["messages"][-1].content
    history = state["messages"][:-1]
    result = executor.invoke({"input": last, "chat_history": history})
    output = result.get("output", "")
    state["messages"].append(AIMessage(content=output))
    state["results"].append(output)
    return state


# Build workflow --------------------------------------------------------------
saver = SqliteSaver.from_conn_string("tool_call_memory.db")

builder = StateGraph(GraphState)
builder.set_entry_point("agent_step")
builder.add_node("agent_step", agent_step)
builder.add_edge("agent_step", END)

workflow = builder.compile(checkpointer=saver)
