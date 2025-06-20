from __future__ import annotations

import asyncio
from features.cours_management.agents.quizzAgent import QuizAgent
from ..graph_state import GraphState

quiz_agent = QuizAgent()


def quiz_node(state: GraphState) -> GraphState:
    """Generate a quiz using QuizAgent."""
    async def _gen():
        return await quiz_agent.generate_quiz_for_chapters_async(-1, [])

    quizzes = asyncio.run(_gen())
    state["result"] = {"response": quizzes}
    return state
