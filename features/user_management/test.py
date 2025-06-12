# features/cours_management/workflow/cours_graph.py

import json
import logging
import operator
from typing import TypedDict, Annotated, List, Optional
from features.cours_management.agents.rag_agent import RAGAgent
import os
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, END
from features.cours_management.memory_course.conversation_memory import ConversationMemory

from features.cours_management.agents.SuggestionAgent import SuggestionAgent
from features.cours_management.agents.schedule_agent import ScheduleAgent
from features.cours_management.agents.cours_agent import CourseAgent
from features.user_management.agents.user_agent import UserAgent
from features.user_management.tools.user_tools import UserTools
from features.chatbot.tools.chatbot_tools import ChatbotTools
from features.cours_management.tools.cours_tools import CourseTools
from features.cours_management.agents.OperationDetectionAgent import OperationDetectionAgent


# --- Typage de l'état du graphe ---
class GraphState(TypedDict):
    messages: Annotated[List[HumanMessage], operator.add]
    detected_operations: List[dict]
    pending_operations: List[dict]
    results: List[dict]
    error: Optional[str]
    pdf_bytes: Optional[bytes]
    user_role: Optional[str]
    user_id: Optional[str]
    rag_context: Optional[str]  # Ajoute cette ligne


# --- Instances des agents / outils ---
schedule_agent = ScheduleAgent()
course_agent = CourseAgent()
user_agent = UserAgent()
chatbot_tools = ChatbotTools()
suggestion_agent = SuggestionAgent()
rag_agent = RAGAgent()
operation_detection_agent = OperationDetectionAgent()

builder = StateGraph(GraphState)
MAX_CONTEXT_LENGTH = 3000
MAX_HISTORY_MESSAGES = 10  # ou 5, selon ton besoin


def truncate_text(text: str, max_length=MAX_CONTEXT_LENGTH) -> str:
    return text if len(text) <= max_length else text[:max_length] + "..."


conversation_memory = ConversationMemory()


# 👉 Assurez-vous d’avoir instancié operation_detection_agent ailleurs :
# operation_detection_agent = OperationDetectionAgent()

def detect_operations(state: GraphState) -> GraphState:
    last_msg_raw = state["messages"][-1].content
    user_role    = (state.get("user_role") or "public").lower()
    user_id      = state.get("user_id")
    pdf_bytes    = state.get("pdf_bytes")
    has_pdf      = bool(pdf_bytes)

    # 0️⃣ Si PDF déposé sans message explicite → conversation synchronisée
    if has_pdf and not last_msg_raw.strip():
        return handle_pdf_actions(state)

    history_context = ""
    if user_id:
        recent_conversations = conversation_memory.get_recent_conversations(user_id)
        count = 0
        for conv in recent_conversations:
            for msg in conv.get("messages", []):
                if count >= MAX_HISTORY_MESSAGES:
                    break
                history_context += f"{msg['role']}: {msg['content']}\n"
                count += 1
        history_context = truncate_text(history_context)

    # 1️⃣ Le routeur LLM renvoie un label
    label_dict   = operation_detection_agent.detect_operation(
        user_input=last_msg_raw,
        user_role=user_role,
        pdf_available=has_pdf,
    )
    label = label_dict.get("category", "chat")

    # 2️⃣ Aiguillage
    if label == "process_pdf":
        if not has_pdf:
            operation = {"operation": "response",
                         "parameters": {"response": "Aucun PDF fourni."}}
        elif user_role not in ("instructor", "professor"):
            operation = {"operation": "response",
                         "parameters": {"response": "Vous n'êtes pas autorisé à importer un PDF"}}
        else:
            operation = {"operation": "process_pdf", "parameters": {"pdf_bytes": pdf_bytes}}

    elif label == "show_calendar":
        operation = {"operation": "show_calendar", "parameters": {}}
    elif label == "answer_course":
        answer = course_agent.answer_course_question(last_msg_raw, course_title="")
        operation = {
            "operation": "response",
            "parameters": {"response": answer["parameters"]["response"]}
        }

    elif label == "get_user_memories":
        memories = conversation_memory.get_recent_conversations(user_id)
        answer = course_agent.answer_about_memories(memories, last_msg_raw)
        operation = {
            "operation": "response",
            "parameters": {"response": answer.get("response", "")}
        }
    elif label == "schedule_session":
        if user_role not in ("instructor", "professor"):
            operation = {"operation": "response",
                         "parameters": {"response": "Seuls les instructeurs peuvent planifier une session live."}}
        else:
            operation = schedule_agent.detect_operation(last_msg_raw)

    elif label == "user":
        operation = user_agent.detect_operation(last_msg_raw)

    elif label == "course":
        operation = course_agent.detect_operation(
            user_input=last_msg_raw,
            history="",            # tu peux injecter history_context si besoin
            memories=state.get("rag_context", "")
        )

    else:  # chat par défaut
        operation = {"operation": "chat", "parameters": {"input": last_msg_raw}}

    # 3️⃣ (Autorisation + persistance) — inchangé
    op_name = operation.get("operation")
    if op_name in ("create_course", "update_course", "delete_course") and user_role not in ("instructor", "professor"):
        operation = {
            "operation": "response",
            "parameters": {"response": f"You are not authorized to perform '{op_name}'."}
        }

    if user_id:
        conversation_memory.save_conversation(
            user_id=user_id,
            messages=state["messages"],
            metadata={"user_role": user_role}
        )

    state["detected_operations"] = [operation]
    state["pending_operations"]  = [operation]
    return state


def execute_operation(state: GraphState) -> GraphState:
    if state["results"] and 'error' in state["results"][0]:
        return state
    if not state["pending_operations"]:
        return {"error": "Aucune opération en attente"}

    operation = state["pending_operations"].pop(0)

    if operation["operation"] == "show_calendar":
        state["results"] = [{"requires_validation": True, "view": "calendar"}]
        state["pending_operations"] = []
        return state

    try:
        if operation["operation"] == "process_pdf":
            pdf = state.get("pdf_bytes") or operation["parameters"].get("pdf_bytes")
            if not pdf:
                state["error"] = "Aucun PDF fourni pour le traitement."
                return state

            process_result = course_agent.process_pdf(pdf)
            if "error" in process_result:
                return {"error": process_result["error"]}

            params = process_result.get("parameters", {})
            params["user_role"] = state.get("user_role")

            state["results"] = [{
                "validation_required": True,
                "operation": "create_course",
                "course_data": params
            }]
            state["pending_operations"] = []
            return state

        tool_name = operation["operation"]
        params = operation.get("parameters", {}) or {}
        params["user_role"] = state.get("user_role", "public")

        if tool_name in ["get_users", "get_user_by_id", "create_user", "update_user", "delete_user"]:
            tool = getattr(UserTools, tool_name, None)
            result = tool.invoke(params) if tool else {"error": f"Outil {tool_name} introuvable"}

        elif tool_name == "create_course":
            state["results"].append({
                "validation_required": True,
                "operation": "create_course",
                "course_data": params
            })
            return state

        elif tool_name in ["get_course_by_id", "get_courses", "delete_course", "update_course",
                           "search_courses_advanced"]:
            tool = getattr(CourseTools, tool_name, None)
            result = tool.invoke(params) if tool else {"error": f"Outil {tool_name} introuvable"}

        elif tool_name == "schedule_session":
            if params["start_time"] >= params["end_time"]:
                state["error"] = "La date de fin doit être après la date de début"
                return state

            state["results"].append({
                "validation_required": True,
                "operation": "schedule_session",
                "session_data": params
            })
            return state


        elif tool_name == "chat":
            chat_text = chatbot_tools.chat_tool.invoke(params.pop("input"))
            result = {"response": chat_text}
            state["results"].append(result)
            return state

        elif tool_name == "response":
            state["results"].append({"response": params.get("response", "")})
            return state

        else:
            return {"error": f"Operation unknown: {tool_name}"}

        state["results"].append(result)

    except Exception as e:
        state["error"] = str(e)

    return state


# 🔧 Compilation du graphe sans mémoire
builder.set_entry_point("detect_operations")
builder.add_node("detect_operations", detect_operations)
builder.add_node("execute_operation", execute_operation)
builder.add_edge("detect_operations", "execute_operation")
builder.add_edge("execute_operation", END)

workflow = builder.compile()  # ✅ sans MemorySaver
