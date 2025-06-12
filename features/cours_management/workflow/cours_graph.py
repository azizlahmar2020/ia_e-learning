# features/cours_management/workflow/cours_graph.py
# ──────────────────────────────────────────────────────────────────────────────
import io, logging, operator
from typing import TypedDict, Annotated, List, Optional

from langgraph.graph          import StateGraph, END
from langchain_core.messages  import HumanMessage, SystemMessage
from PyPDF2                   import PdfReader

from features.cours_management.memory_course.conversation_memory import ConversationMemory
from features.cours_management.agents.rag_agent        import RAGAgent
from features.cours_management.agents.SummarizeAgent   import UnifiedCourseAgent
from features.cours_management.agents.PDFInteractionAgent import PDFInteractionAgent
from features.cours_management.agents.quizzAgent       import QuizAgent
from features.cours_management.agents.SuggestionAgent  import SuggestionAgent
from features.cours_management.agents.schedule_agent   import ScheduleAgent
from features.cours_management.agents.cours_agent      import CourseAgent
from features.cours_management.agents.OperationDetectionAgent import OperationDetectionAgent
from features.user_management.agents.user_agent        import UserAgent
from features.user_management.tools.user_tools         import UserTools
from features.cours_management.tools.cours_tools       import CourseTools
from features.chatbot.tools.chatbot_tools              import ChatbotTools
from features.cours_management.memory_course.agent_memory import AgentMemory

# ──────────────────────────────────────────────────────────────────────────────

# 1. État ─────────────────────────────────────────────────────────────────────
class GraphState(TypedDict):
    messages           : Annotated[List[HumanMessage], operator.add]
    detected_operations: List[dict]
    pending_operations : List[dict]
    results            : List[dict]
    error              : Optional[str]
    pdf_bytes          : Optional[bytes]
    user_role          : Optional[str]
    user_id            : Optional[str]
    conversation_id    : str
    rag_context        : Optional[str]
    history_list       : Optional[List[str]]

# 2. Instances globales ───────────────────────────────────────────────────────
conversation_memory = ConversationMemory()
schedule_agent   = ScheduleAgent()
course_agent     = CourseAgent()
user_agent       = UserAgent()
chatbot_tools    = ChatbotTools()
suggestion_agent = SuggestionAgent()
rag_agent        = RAGAgent()
router           = OperationDetectionAgent()
summ_agent       = UnifiedCourseAgent()
quiz_agent       = QuizAgent()
pdf_agent = PDFInteractionAgent()
system_memory    = AgentMemory(agent_type="system")

builder            = StateGraph(GraphState)
MAX_CONTEXT_LENGTH = 3_000
MAX_HISTORY        = 10

# 3. Utilitaires ──────────────────────────────────────────────────────────────
def truncate(txt: str, n: int = MAX_CONTEXT_LENGTH) -> str:
    return txt if len(txt) <= n else txt[:n] + "…"

def _extract_text(pdf: bytes) -> str:
    try:
        with io.BytesIO(pdf) as buf:
            return "\n".join((page.extract_text() or "") for page in PdfReader(buf).pages)
    except Exception as e:
        logging.warning("PDF extraction failed: %s", e)
        return ""

# 4. Routage ─ detect_operations ─────────────────────────────────────────────
def detect_operations(state: GraphState) -> GraphState:
    last      = state["messages"][-1].content
    role      = (state.get("user_role") or "public").lower()
    user_id   = state.get("user_id") or ""
    conv_id   = state["conversation_id"]
    pdf       = state.get("pdf_bytes")
    has_pdf   = bool(pdf)

    # 0️⃣ PDF sans message → suggestions
    if has_pdf and not last.strip():
        suggestions = course_agent.generate_pdf_suggestions(role)
        op = {"operation": "response", "parameters": {"response": suggestions}}
        state["detected_operations"] = [op]
        state["pending_operations"]  = [op]
        state["history_list"] = []
        return state

    # 1️⃣ Historique + Mémoire enrichie
    raw_history = []
    hist_ctx = ""
    for conv in conversation_memory.get_recent_conversations(user_id, conv_id, MAX_HISTORY):
        for m in conv.get("messages", []):
            entry = f"{m['role'].capitalize()}: {m['content']}"
            raw_history.append(entry)
            hist_ctx += entry + "\n"
    hist_ctx = truncate(hist_ctx)
    state["history_list"] = raw_history

    try:
        prefs = system_memory.get_user_preferences(user_id)
        mem_info = f"Préférences utilisateur: {prefs}\n"
    except Exception:
        mem_info = ""

    rag_info = state.get("rag_context", "")
    system_intro = f"Vous êtes un assistant intelligent.\n{mem_info}\n{hist_ctx}\nConnaissances disponibles:\n{rag_info}".strip()
    state["messages"].insert(0, SystemMessage(content=truncate(system_intro, MAX_CONTEXT_LENGTH)))

    # 2️⃣ Détection
    label = router.detect_category(
        last, role, has_pdf,
        history=hist_ctx,
        user_id=user_id,
        conversation_id=conv_id
    )
    print (label)
    # 3️⃣ Mapping label → opération
    if label == "process_pdf":
        if not has_pdf:
            op = {"operation": "response", "parameters": {"response": "Aucun PDF fourni."}}
        elif role not in {"instructor", "professor"}:
            op = {"operation": "response", "parameters": {"response": "Vous n'êtes pas autorisé à importer un PDF."}}
        else:
            op = {"operation": "process_pdf", "parameters": {"pdf_bytes": pdf}}

    elif label == "summarize":
        raw_text = _extract_text(pdf) if has_pdf else last
        op = {"operation": "summarize", "parameters": {
            "text": raw_text,
            "user_message": last
        }}

    elif label == "qa":
        op = {"operation": "qa", "parameters": {"question": last}}

    elif label == "quiz":
        op = {"operation": "quiz", "parameters": {}}

    elif label == "show_calendar":
        op = {"operation": "show_calendar", "parameters": {}}

    elif label == "schedule_session":
        op = schedule_agent.detect_operation(last) if role in {"instructor", "professor"} else {"operation": "response", "parameters": {"response": "Seuls les instructeurs peuvent planifier une session live."}}

   
    elif label == "get_user_memories":
        mem = conversation_memory.get_recent_conversations(user_id)
        ans = course_agent.answer_about_memories(mem, last)
        op  = {"operation": "response", "parameters": {"response": ans.get("response", "")}}

    elif label == "user":
        op = user_agent.detect_operation(last)

    elif label == "course":
        op = course_agent.detect_operation(user_input=last, history=hist_ctx, memories=rag_info)

    else:  # fallback
        op = {"operation": "chat", "parameters": {"input": last, "history": hist_ctx}}

    # 4️⃣ Contrôle accès étudiant
    if op["operation"] in {"create_course", "update_course", "delete_course"} and role == "student":
        op = {"operation": "response", "parameters": {"response": "Vous n’êtes pas autorisé à modifier les cours."}}

    state["detected_operations"] = [op]
    state["pending_operations"]  = [op]
    return state

# 5. Exécution ─ execute_operation ───────────────────────────────────────────
def execute_operation(state: GraphState) -> GraphState:
    if state.get("error") or not state["pending_operations"]:
        return state

    op       = state["pending_operations"].pop(0)
    name     = op["operation"]
    params   = op.get("parameters", {}) or {}
    role     = (state.get("user_role") or "public").lower()
    user_id  = state.get("user_id") or ""
    conv_id  = state["conversation_id"]
    history  = state.get("history_list") or []

    try:
        # Calendrier --------------------------------------------------------
        if name == "show_calendar":
            state["results"] = [{"requires_validation": True, "view": "calendar"}]

        # Import PDF --------------------------------------------------------
        elif name == "process_pdf":
            pdf = state.get("pdf_bytes") or params.get("pdf_bytes")
            if not pdf:
                raise ValueError("Aucun PDF fourni.")
            res = course_agent.process_pdf(pdf)
            if "error" in res:
                raise RuntimeError(res["error"])
            res["parameters"]["user_role"] = role
            state["results"] = [{
                "validation_required": True,
                "operation": "create_course",
                "course_data": res["parameters"]
            }]

        # Résumé ------------------------------------------------------------
        elif name == "summarize":
            text = params.get("text", "")
            user_msg = params.get("user_message", "")
            summary = pdf_agent.run(
                raw_text=text,
                user_message=user_msg,
                user_id=user_id,
                conversation_id=conv_id
            )

            print (summary)
            state["results"].append({"response": summary})

        # QA ---------------------------------------------------------------


        # Création de cours (owner_id auto) ---------------------------------
        elif name == "create_course":
            params["owner_id"] = user_id
            state["results"].append({
                "validation_required": True,
                "operation": "create_course",
                "course_data": params
            })

        # Update / Delete : contrôle propriétaire ---------------------------
        elif name in {"update_course", "delete_course"}:
            if role == "student":
                state["results"].append({"error": "Action non autorisée pour les étudiants."})
            else:
                course_id = params.get("course_id")
                if not course_id:
                    state["results"].append({"error": "course_id manquant"})
                else:
                    course = CourseTools.get_course_by_id.invoke({"course_id": course_id}).get("course")
                    owner_id = course.get("owner_id") if course else None
                    if owner_id and str(owner_id) != user_id and role in {"instructor", "professor"}:
                        state["results"].append({"error": "Vous ne pouvez modifier que vos propres cours."})
                    else:
                        tool = getattr(CourseTools, name)
                        state["results"].append(tool.invoke(params))

        # Lecture / recherche cours ----------------------------------------
        elif name in {"get_course_by_id", "search_courses_advanced"}:
            tool = getattr(CourseTools, name)
            state["results"].append(tool.invoke(params))
        elif name == "schedule_session":
            # contrôle simple des dates
            if params["start_time"] >= params["end_time"]:
                state["error"] = "La date de fin doit être après la date de début"
                return state

            state["results"].append({
                "validation_required": True,
                "operation": "schedule_session",
                "session_data": params
            })
            return state
        # Quiz --------------------------------------------------------------
        elif name == "quiz":
            quizzes = quiz_agent.generate_quiz_for_chapters_async(-1, params.get("chapters", []))
            state["results"].append({"response": quizzes})

        # Chat --------------------------------------------------------------
        elif name == "chat":
            txt = chatbot_tools.chat_tool.invoke(params.pop("input"))
            state["results"].append({"response": txt})
        elif name == "answer_course":
            # Nouvelle prise en charge de la question sur le cours
            ans = course_agent.answer_course_question(params.get("question", ""), params.get("course_title", ""))
            state["results"] = [{"response": ans.get("parameters", {}).get("response", "")}]

        # Réponse prête -----------------------------------------------------
        elif name == "response":
            state["results"].append({"response": params.get("response", "")})

        # Opération utilisateur (CRUD) -------------------------------------
        elif name.startswith(("get_user", "create_user", "update_user", "delete_user")):
            tool = getattr(UserTools, name)
            state["results"].append(tool.invoke(params))

        else:  # inconnu
            state["results"].append({"error": f"Opération inconnue : {name}"})

        # Enregistrement de la réponse assistant avec le dernier message user
        if state["results"]:
            responses = []
            for r in state["results"]:
                if "response" in r:
                    responses.append(str(r["response"]))
                else:
                    responses.append(str(r))
            ai_txt = "\n".join(responses)

            user_msg = ""
            for msg in reversed(state["messages"]):
                if msg.type == "human":
                    user_msg = msg.content
                    break

            if user_msg.strip() or ai_txt.strip():
                conversation_memory.save_conversation(
                    user_id=user_id,
                    user_message=user_msg,
                    assistant_message=ai_txt,
                    conversation_id=conv_id,
                    meta={"stage": "exchange", "user_role": role}
                )

    except Exception as e:
        state["error"] = str(e)

    return state

# 6. Compilation du graphe ───────────────────────────────────────────────────
builder.set_entry_point("detect_operations")
builder.add_node("detect_operations", detect_operations)
builder.add_node("execute_operation",  execute_operation)
builder.add_edge("detect_operations", "execute_operation")
builder.add_edge("execute_operation", END)

workflow = builder.compile()
# ──────────────────────────────────────────────────────────────────────────────
