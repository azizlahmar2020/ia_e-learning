# -*- coding: utf-8 -*-
"""
FastAPI router « courses » — mémoire par discussion + fallback PDF utilisateur
--------------------------------------------------------------------------
Version corrigée avec synchronisation améliorée et gestion de la mémoire unifiée
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from typing import Optional, Dict, Any, List

from fastapi import (
    APIRouter,
    HTTPException,
    UploadFile,
    Request,
    Header,
    Depends,
)
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

from features.user_management.api import get_current_user
from features.cours_management.memory_course.memory_singleton import MemorySingleton
from features.cours_management.utils.conversation_utils import normalize_conversation_id, create_conversation_key
from features.cours_management.utils.pdf_cache import PDFCache
from features.cours_management.workflow.cours_graph import workflow, suggestion_agent
from features.cours_management.agents.ContentAgent import ContentAgent
from features.cours_management.agents.rag_agent import RAGAgent
from features.cours_management.tools.cours_tools import CourseTools
from features.cours_management.tools.schedule_tools import ScheduleTools
from features.chatbot.agents.chatbot_agent import ChatbotAgent
logger = logging.getLogger(__name__)

# Initialisation des singletons pour une gestion unifiée de la mémoire
conversation_memory = MemorySingleton.get_conversation_memory()
qdrant_rag = MemorySingleton.get_qdrant_rag()
pdf_cache = PDFCache(ttl_seconds=15 * 60)  # 15 minutes
rag_agent = RAGAgent()

router = APIRouter(prefix="/courses", tags=["courses"])


class ChapterInput(BaseModel):
    title: str
    content: str


class GeneratedChapter(BaseModel):
    Title: str
    Content: str


class SearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 3


# ───────────────────── /chat ─────────────────────
@router.post("/chat")
async def chat_endpoint(
        request: Request,
        current_user: dict = Depends(get_current_user),
        x_conversation_id: Optional[str] = Header(None, alias="X-Conversation-Id"),
):
    try:
        # ───── Préambule ───────────────────────────────────────────
        user_id   = str(current_user.get("user_id") or current_user.get("id"))
        if not user_id:
            raise HTTPException(401, "Token sans user_id")
        user_role = (current_user.get("user_role") or "public").lower()

        body_json = await request.json() if request.headers.get("content-type","").startswith("application/json") else {}
        conv_id   = normalize_conversation_id(x_conversation_id or body_json.get("conversation_id") or "")

        # ───── Message + PDF éventuel ─────────────────────────────
        message   = body_json.get("message","") if body_json else ""
        pdf_bytes = None
        if "multipart/form-data" in request.headers.get("content-type",""):
            form    = await request.form()
            message = (form.get("message") or "").strip()
            upload  = form.get("file")
            if upload and upload.filename.lower().endswith(".pdf"):
                pdf_bytes = await upload.read()
                pdf_cache.store(user_id, pdf_bytes, conv_id, pending=not message)
        else:
            pdf_bytes, _, _ = pdf_cache.retrieve(user_id, conv_id)

        if not message and not pdf_bytes:
            return {"conversation_id": conv_id, "response": "Aucun PDF fourni."}

        # ───── Historique & RAG ───────────────────────────────────
        hist      = conversation_memory.get_recent_conversations(user_id, conv_id, 10)
        hist_msgs = conversation_memory.reconstruct_messages(hist)
        all_msgs  = (hist_msgs + [HumanMessage(content=message)])[-10:]

        rag_ctx = ""
        try:
            rag_ctx = rag_agent.process_query(message,
                                              history_context="\n".join(m.content for m in hist_msgs)
                                             ).get("enriched_context","")
        except Exception:
            pass

        # ───── exécution LangGraph ────────────────────────────────
        state = {
            "messages": all_msgs,
            "pending_operations": [],
            "detected_operations": [],
            "user_role": user_role,
            "user_id": user_id,
            "conversation_id": conv_id,
            "results": [],
            "error": None,
            "rag_context": rag_ctx,
            "pdf_bytes": pdf_bytes,
        }

        thread_id = create_conversation_key(user_id, conv_id)
        wf_res    = workflow.invoke(state, {"configurable": {"thread_id": thread_id}})

        # si on avait un PDF en attente → on marque comme traité
        if pdf_bytes:
            for r in wf_res["results"]:
                if r.get("operation") == "process_pdf":
                    _, _, k = pdf_cache.retrieve(user_id, conv_id)
                    if k:
                        pdf_cache.update_status(k, False)
                    break



        # validations…
        if wf_res["results"]:
            for r in wf_res["results"]:
                if r.get("validation_required"):
                    view = "session" if r["operation"] == "schedule_session" else "cours"
                    key  = "session_data" if view == "session" else "course_data"
                    return {
                        "conversation_id": conv_id,
                        "requires_validation": True,
                        "view": view,
                        "message": "Veuillez valider",
                        key: r[key]
                    }
            return {"conversation_id": conv_id, "response": wf_res["results"], "message": message}

        return {"conversation_id": conv_id, "response": "Aucune réponse générée."}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("/chat error")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ────────────────────────────────────────────────
# Suggestions rapides (hors workflow)
# ────────────────────────────────────────────────

@router.get("/suggestion/{user_id}")
async def get_suggestion(user_id: str):
    try:
        return {"suggestion": suggestion_agent.suggest(user_id)}
    except Exception as e:
        logger.error("Suggestion error: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


# ────────────────────────────────────────────────
# Validation (cours ou session) & indexation RAG
# ────────────────────────────────────────────────

@router.post("/validate")
async def validate(request: Request):
    try:
        raw = await request.json()
        data = raw.get("data", raw)

        # ----- cours -----
        if "course_data" in data:
            container = data["course_data"]
            course_data = (
                container.get("course_data")
                if isinstance(container, dict) and "course_data" in container
                else container
            )
            if not course_data:
                raise HTTPException(400, "Missing course_data")
            result = await CourseTools.create_course(course_data)
            if err := result.get("error"):
                return JSONResponse(content={"error": err}, status_code=500)

            course_id = result.get("course_id")
            if course_id and qdrant_rag and qdrant_rag.is_available:
                try:
                    qdrant_rag.add_course_content(
                        course_id=course_id,
                        title=course_data.get("title", ""),
                        content=course_data.get("content", ""),
                        metadata=course_data,
                    )
                except Exception as e:
                    logger.error("Indexation Qdrant failed: %s", e)

            return {"message": "Cours créé avec succès", "data": result}

        # ----- session live -----
        if "session_data" in data:
            sess = data["session_data"]
            if not sess:
                raise HTTPException(400, "Missing session_data")
            res = ScheduleTools.validate_session(sess)
            if err := res.get("error"):
                return JSONResponse(500, content={"error": err})
            return {"message": "Session programmée avec succès", "data": res}

        raise HTTPException(400, "course_data or session_data required")

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Validate endpoint error")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ────────────────────────────────────────────────
# RAG Search
# ────────────────────────────────────────────────

@router.post("/search")
async def search_knowledge(search: SearchRequest, current_user: dict = Depends(get_current_user)):
    try:
        if not qdrant_rag or not qdrant_rag.is_available:
            return {
                "warning": "Recherche sémantique indisponible",
                "query": search.query,
                "results": [],
            }
        results = qdrant_rag.search_with_score(search.query, k=search.limit)
        return {
            "query": search.query,
            "results": [
                {"content": doc.page_content, "metadata": doc.metadata, "relevance": score}
                for doc, score in results
            ],
        }
    except Exception as e:
        logger.error("Search endpoint error: %s", e)
        return JSONResponse(status_code=500, content={"error": str(e)})


# ────────────────────────────────────────────────
# Génération de chapitre (LLM)
# ────────────────────────────────────────────────

content_agent = ContentAgent()
chatbot_agent = ChatbotAgent()


@router.post("/askme")
async def askme_endpoint(request: Request):
    try:
        body = await request.json()
        message = body.get("message", "")
        if not message.strip():
            raise HTTPException(400, "Message cannot be empty.")

        # Get chatbot response
        response = chatbot_agent.get_response(message)

        return {"response": response}
    except Exception as e:
        logger.exception("/askme error")
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.post("/generate_chapter", response_model=GeneratedChapter)
async def generate_chapter(chapter: ChapterInput):
    try:
        return content_agent.generate_content_for_chapter(chapter.dict())
    except Exception as e:
        logger.error("Generate chapter error: %s", e)
        raise HTTPException(500, str(e))


# ────────────────────────────────────────────────
# Indexation RAG manuelle
# ────────────────────────────────────────────────

@router.post("/index_course/{course_id}")
async def index_course(course_id: str, current_user: dict = Depends(get_current_user)):
    try:
        if (current_user.get("user_role", "").lower() not in {"instructor", "professor", "admin"}):
            raise HTTPException(403, "Non autorisé")
        if not qdrant_rag or not qdrant_rag.is_available:
            return {"warning": "Qdrant indisponible"}
        course_res = CourseTools.get_course_by_id({"course_id": course_id})
        if err := course_res.get("error"):
            return JSONResponse(404, content={"error": err})
        course = course_res.get("course")
        qdrant_rag.delete_by_course_id(course_id)
        qdrant_rag.add_course_content(course_id, course.get("title", ""), course.get("content", ""), metadata=course)
        return {"message": "Indexation réussie", "course_id": course_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Index course error: %s", e)
        return JSONResponse(500, content={"error": str(e)})


@router.post("/index_all_courses")
async def index_all_courses(current_user: dict = Depends(get_current_user)):
    try:
        if current_user.get("user_role", "").lower() not in {"instructor", "professor", "admin"}:
            raise HTTPException(403, "Non autorisé")
        if not qdrant_rag or not qdrant_rag.is_available:
            return {"warning": "Qdrant indisponible"}
        courses = CourseTools.get_courses({}).get("courses", [])
        ok, ko = 0, []
        for c in courses:
            cid = c.get("id")
            try:
                qdrant_rag.delete_by_course_id(cid)
                qdrant_rag.add_course_content(cid, c.get("title", ""), c.get("content", ""), metadata=c)
                ok += 1
            except Exception as e:
                ko.append({"course_id": cid, "title": c.get("title"), "error": str(e)})
        return {"indexed": ok, "failed": ko}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Index all courses error: %s", e)
        return JSONResponse(500, content={"error": str(e)})


# ────────────────────────────────────────────────
# Health endpoint
# ────────────────────────────────────────────────

@router.get("/qdrant_status")
async def qdrant_status():
    return {
        "memory_available": getattr(conversation_memory, "is_available", False),
        "rag_available": getattr(qdrant_rag, "is_available", False),
    }


