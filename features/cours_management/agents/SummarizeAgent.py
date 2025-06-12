from __future__ import annotations
import logging, os, re, textwrap, json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
import requests
from features.cours_management.memory_course.agent_memory import AgentMemory

load_dotenv()
_LOG = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
_CHUNK_CHARS = 8000
_OVERLAP_CHARS = 600
_RATIO_MIN = 0.05

class UnifiedCourseAgent:
    def __init__(self):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=_CHUNK_CHARS,
            chunk_overlap=_OVERLAP_CHARS,
        )
        self.memory = AgentMemory(agent_type="pdf_interaction")

    def _call_deepseek(self, prompt: str) -> str:
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json"
                },
                data=json.dumps({
                    "model": "deepseek/deepseek-coder:6.7b",
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                }),
                timeout=30
            )
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        except Exception as e:
            _LOG.error(f"[DeepSeek] API error: {e}")
            return ""

    def run(self,
            raw_text: str,
            user_message: str,
            user_id: Optional[str] = None,
            conversation_id: Optional[str] = None
        ) -> Any:
        if not raw_text.strip():
            return "Aucun contenu fourni."

        context = self._clean(raw_text)
        history = []
        if user_id:
            history = [f"{r['query']} → {r['response']}" for r in self.memory.get_recent_responses(user_id, conversation_id)]

        return self._unified_response(context, user_message, history, user_id, conversation_id)

    def _unified_response(
        self,
        context: str,
        user_message: str,
        history: List[str],
        user_id: Optional[str],
        conversation_id: Optional[str]
    ) -> str:
        history_block = "\n".join(history)
        prompt = textwrap.dedent(f"""
        Tu es un assistant e-learning expert qui répond à toutes les questions concernant un PDF donné.

        CONTEXTE DU PDF :
        {context}

        MESSAGE UTILISATEUR :
        {user_message}

        HISTORIQUE DES MESSAGES :
        {history_block}

        INSTRUCTIONS :
        - Analyse le message et fournis une réponse adaptée (explication, résumé, reformulation, quiz si demandé).
        - Si l'utilisateur demande une version plus détaillée, améliore la dernière réponse mémorisée.
        - Si l'utilisateur demande un quiz, retourne ce format :
          {{
            "view": "quiz",
            "questions": [
              {{"question": "...", "options": ["..."], "answer": 0}}
            ]
          }}
        - Ne réponds jamais par une phrase générique.
        - Utilise uniquement le contenu du PDF et le contexte pour justifier tes réponses.
        """).strip()

        try:
            result = self._call_deepseek(prompt)
            if user_id:
                self.memory.save_response(user_id=user_id, conversation_id=conversation_id or "", query=user_message, response=result, metadata={"mode": "auto"})
            try:
                parsed = json.loads(result)
                if isinstance(parsed, dict) and parsed.get("view") == "quiz":
                    return parsed
            except json.JSONDecodeError:
                pass
            return result
        except Exception as e:
            _LOG.error(f"Erreur unified prompt: {e}")
            return "Erreur lors du traitement."

    def _clean(self, text: str) -> str:
        text = re.sub(r'\n\d+\s+\d+\s+obj[\s\S]*?endobj', ' ', text)
        text = re.sub(r'stream.*?endstream', ' ', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'/[A-Za-z0-9]+\b', ' ', text)
        text = re.sub(r'\(.*?\)', ' ', text)
        text = re.sub(r'[\x00-\x1F]', ' ', text)
        lines = text.splitlines()
        keep = []
        alpha = re.compile(r'[A-Za-zÀ-ÖØ-öø-ÿ]')
        for ln in lines:
            ln = re.sub(r'\s+', ' ', ln).strip()
            if len(ln) >= 60 and len(alpha.findall(ln)) / max(len(ln), 1) >= _RATIO_MIN:
                keep.append(ln)
        return ' '.join(keep)
