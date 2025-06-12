from __future__ import annotations
import json, os, re, textwrap, logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import requests

from features.cours_management.memory_course.agent_memory import AgentMemory

load_dotenv()
_LOG = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

_PROMPT = textwrap.dedent("""
Tu es un **Routeur d'opérations** (Operation Router) pour un chatbot e-learning.
Ta seule mission : lire le message utilisateur + contexte, puis renvoyer EXACTEMENT
un objet JSON compact à UNE seule clé : "category".

══════════════════════════════════════════════════════════════════════════════
CATEGORIES AUTORISÉES
─────────────────────
1. "process_pdf"       → cree cours uniquement lorsqu'un PDF attaché.
2. "show_calendar"     → consulter l'agenda / calendrier.
3. "schedule_session"  → interroger une session live.
4. "get_user_memories" → afficher l'historique utilisateur.
5. "user"              → opérations sur le compte utilisateur.
6. "course"            → creation et recherche des cours.
7. "summarize"         → demander un résumé/question/explication du pdf.

══════════════════════════════════════════════════════════════════════════════
CONTEXTES FOURNIS AU ROUTEUR
────────────────────────────
role            = rôle de l'utilisateur
pdf_present     = true / false
message         = contenu brut du message utilisateur
history         = historique récent des catégories détectées
last_agent_used = nom de l'agent qui a répondu précédemment (ex: 'pdf_interaction', 'course_agent', null)

══════════════════════════════════════════════════════════════════════════════
EXEMPLES :
──────────
• message = "Planifie une session demain"      → {"category": "schedule_session"}
• message = "Résumé du contenu joint"          → {"category": "summarize"}
• message = "Importer ce fichier PDF"          → {"category": "process_pdf"}
• message = "Non, mieux que ça" (si last_agent_used='pdf_interaction') → {"category": "summarize"}
• message = "Create new course about .NET"     → {"category": "course"}

IMPORTANT : Choisis la catégorie LA PLUS PERTINENTE selon l’intention du message,
même si un fichier PDF est attaché. Prends en compte `last_agent_used` pour les demandes de suivi.

RÈGLES DE SORTIE
────────────────
Réponds strictement MINIFIÉ, JSON seul : {"category":"..."}.
""")

class OperationDetectionAgent:
    def __init__(self):
        self.memory = AgentMemory(agent_type="operation_detection")

    def _call_deepseek(self, prompt: str) -> str:
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                data=json.dumps({
                    "model": "deepseek/deepseek-chat:latest",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                }),
                timeout=20
            )
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            return content.strip()
        except Exception as e:
            _LOG.error(f"[DeepSeek] API error: {e}")
            return '{"category":"chat"}'

    def detect_category(
        self,
        user_message: str,
        user_role: str = "public",
        has_pdf: bool = False,
        history: str = "",
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        last_agent_used: Optional[str] = None
    ) -> str:
        if not user_message or not user_message.strip():
            return "chat"

        prompt = _PROMPT + textwrap.dedent(f"""
        Contexte :
        • role            = {user_role}
        • pdf_present     = {str(has_pdf).lower()}
        • message         = \"\"\"{user_message.strip()}\"\"\"
        • history         = \"\"\"{history.strip()}\"\"\"
        • last_agent_used = {last_agent_used or 'null'}
        """)

        raw = self._call_deepseek(prompt)
        raw = re.sub(r"^```json|```$", "", raw, flags=re.IGNORECASE).strip()

        valid = [
            "process_pdf", "show_calendar", "schedule_session",
            "answer_course", "get_user_memories", "user",
            "course", "chat", "summarize", "qa", "quiz"
        ]

        cat = "chat"
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and "category" in data:
                cat = data["category"]
            elif isinstance(data, str):
                cat = data.strip('"')
        except Exception:
            match = re.search(r'"category"\s*:\s*"([^"]+)"', raw)
            if match:
                cat = match.group(1)

        if cat not in valid:
            cat = "chat"

       # if user_id:
        #    self.memory.save_response(
         #       user_id=user_id,
          #      conversation_id=conversation_id or "",
           #     query=user_message,
            #    response=cat,
             #   metadata={"history": history}
            #)

        _LOG.info(f"[Router] Message: {user_message} → Catégorie: {cat}")
        return cat

    def detect_operation(
        self,
        user_input: str,
        user_role: str = "public",
        user_id: Optional[str] = None,
        pdf_available: bool = False,
        conversation_id: Optional[str] = None,
        history: str = "",
        **ignored
    ) -> Dict[str, Any]:
        category = self.detect_category(
            user_input,
            user_role,
            pdf_available,
            history,
            user_id,
            conversation_id
        )
        return {"category": category}
