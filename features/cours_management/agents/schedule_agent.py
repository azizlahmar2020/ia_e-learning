# 📁 features/cours_management/agents/schedule_agent.py
from __future__ import annotations

import os, json, textwrap, requests, urllib.parse
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from features.cours_management.prompts.schedule_prompt import schedule_prompt,Message_Response
from features.cours_management.tools.schedule_tools import ScheduleTools

now_utc = datetime.now(timezone.utc)
UTC_NOW = now_utc.astimezone()  # Fuseau horaire local (ex: Tunisie = UTC+1)


class ScheduleAgent:
    """Route ⬇️
       • create → ScheduleTools.create_session   (brouillon + validation UI)
       • query  → ScheduleTools.query_sessions   (recherche API)
    """

    # ───────────────────────── init ─────────────────────────
    def __init__(self) -> None:
        load_dotenv()
        self.llm = ChatGroq(
            model_name="llama3-8b-8192",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.3,
        )

    # ────────────────── utilitaire parse JSON ──────────────────
    @staticmethod
    def _safe_json(txt: str) -> Optional[Dict[str, Any]]:
        try:
            cleaned = txt.strip().replace("```json", "").replace("```", "").strip()
            parsed = json.loads(cleaned)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            return None

    def detect_operation(self, user_input: str):
        """
        ⚠️ Méthode conservée pour compatibilité avec l’ancien code.
        Elle délègue simplement à handle().
        """
        return self.handle(user_input)
    # ────────────────── point public ──────────────────
    def handle(self, user_input: str) -> Dict[str, Any]:
        """
        Analyse la requête, détecte l’opération, puis appelle le tool adéquat.
        """
        # 1) Détection intent (create | query)
        detection_prompt = f"""
You are an intent-router for live-session management.

⚠️ Return ONLY valid JSON — no markdown.

Rules  

    Current date: {UTC_NOW}

        1. If the user wants to **create** a new live session, return:  
        Rules:
            - If a course ID is detected, return: {{ "course_id": 123 }}
            - If no specific course is mentioned, return: {{ "course_id": null }}
        {{
             "operation": "create",
             "course_id": 123 | null    // null when no course is mentioned
        }}

       2. If the user wants to **consult / query** live sessions (with or without filters), return:  
   {{
     "operation": "query",
     "filters": {{
       "P_INSTRUCTOR_ID":   int        | null,
       "P_ROOM_NAME":       "string"   | null,   // LIKE %value%
       "P_COURSE_TITLE":    "string"   | null,   // LIKE %value%
       "P_START_DATE_FROM": "YYYY-MM-DD" | null,
       "P_START_DATE_TO":   "YYYY-MM-DD" | null,
       "P_TIME_FROM":       "HH24:MI" | null,
       "P_TIME_TO":         "HH24:MI" | null,
       "P_DATE_TYPE":       "START" or "END" | null,
       "P_ORDER_BY":        "ASC" or "DESC" | null,
       "P_LIMIT":           integer | null
     }}
   }}
4. if the user talk about present information for exemple when my next live session, return:     - Set BOTH `P_START_DATE_FROM` and `P_START_DATE_TO` to that exact date (format: YYYY-MM-DD) of current date
3. ⚠️ If the user is asking about sessions for a **specific day** (e.g., "yesterday", "May 13", "on Tuesday" ,"Tomorrow"), then:
   - Determine the exact date (based on the current date)
   - Set BOTH `P_START_DATE_FROM` and `P_START_DATE_TO` to that exact date (format: YYYY-MM-DD)

4. If the user says things like:
   - "first session" → `P_ORDER_BY: "ASC"`, `P_LIMIT: 1`
   - "last session" → `P_ORDER_BY: "DESC"`, `P_LIMIT: 1`
   - "first 3 sessions" → `P_ORDER_BY: "ASC"`, `P_LIMIT: 3`
   - "last 5 sessions" → `P_ORDER_BY: "DESC"`, `P_LIMIT: 5`
   - If it's about **start time**, set `P_DATE_TYPE: "START"`; if about **end time**, set `P_DATE_TYPE: "END"`

5. Do **not invent filters**. Leave any unspecified field as null.

User input:  
"{user_input}"
        """
        print(UTC_NOW)
        prompt_txt_detect = textwrap.dedent(detection_prompt)

        detection_raw = self.llm.invoke(textwrap.dedent(prompt_txt_detect)).content
        intent = self._safe_json(detection_raw) or {}
        op = intent.get("operation")

        # 2) ─────────────  QUERY  ─────────────
        if op == "query":
            filters = intent.get("filters", {}) or {}
            sessions_result = ScheduleTools.query_sessions(filters)
            sessions = sessions_result.get("sessions", [])

            # 🎯 Construire prompt pour LLM
            prompt = Message_Response.format(
                user_input=user_input,
                sessions_json=json.dumps(sessions, indent=2),
                current_datetime=UTC_NOW
            )

            try:
                message = self.llm.invoke(prompt).content.strip()
            except Exception as e:
                message = "⚠️ Failed to generate a response: " + str(e)

            return {
                "operation": "response",
                "parameters": {
                    "response": {
                        "message": message,
                        "sessions": sessions
                    }
                }
            }

        # 3) ─────────────  CREATE  ─────────────
        if op == "create":
            course_id = intent.get("course_id")
            course_data = {"course_id": None, "title": "", "description": ""}

            if course_id is not None:
                try:
                    r = requests.get(
                        f"https://apex.oracle.com/pls/apex/naxxum/course/{course_id}",
                        headers={
                            "Content-Type": "application/json",
                            "User-Agent": "Mozilla/5.0"
                        },                        timeout=10,
                    )
                    r.raise_for_status()
                    jd = r.json()
                    course_data.update(
                        {
                            "course_id": jd.get("course_id"),
                            "title": jd.get("title", ""),
                            "description": jd.get("description", ""),
                        }
                    )
                except Exception:
                    # garde course_data nulle si l’API échoue
                    pass

            # Génération de l’objet session complet
            prompt_txt = schedule_prompt.format(
                input=user_input,
                sysdate=UTC_NOW,
                course_id=course_data["course_id"],
                course_title=course_data["title"],
                course_description=course_data["description"],
            )
            raw = self.llm.invoke(prompt_txt).content
            session_obj = self._safe_json(raw) or {}

            required = {
                "instructor_id",
                "room_name",
                "title",
                "start_time",
                "end_time",
            }
            if not required.issubset(session_obj):
                return {
                    "operation": "chat",
                    "parameters": {
                        "input": "Informations insuffisantes pour créer la session."
                    },
                }

            return {
                "operation": "schedule_session",
                "parameters": session_obj
            }

        # 4) ─────────────  fallback ─────────────
        return {"operation": "chat", "parameters": {"input": user_input}}
