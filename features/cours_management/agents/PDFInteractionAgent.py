# features/cours_management/agents/PDFInteractionAgent.py
import os, logging, textwrap
from typing import Optional
from dotenv import load_dotenv
from langchain_groq import ChatGroq

from features.cours_management.memory_course.agent_memory import AgentMemory

load_dotenv()
_LOG = logging.getLogger(__name__)

class PDFInteractionAgent:
    """
    Agent d’interaction PDF — résume, explique, génère QCM et sait
    reformuler la DERNIÈRE réponse si l’utilisateur le demande.
    """

    def __init__(self, model: str = "llama3-8b-8192"):
        self.llm = ChatGroq(
            model_name=model,
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.3
        )
        self.memory = AgentMemory(agent_type="pdf_agent")

    # ──────────────────────────────────────────────────────────────
    # PRIVATE
    def _build_prompt(
        self,
        user_msg: str,
        context: str,
        last_answer: str = ""
    ) -> str:
        """Construit un prompt riche : contexte PDF + éventuelle dernière réponse."""
        return textwrap.dedent(f"""
            ### CONTEXTE (extrait du PDF ou cours)
            {context or "⟨vide⟩"}

            ### DERNIÈRE_RÉPONSE (si disponible)
            {last_answer or "⟨aucune⟩"}

            ### DEMANDE_UTILISATEUR
            {user_msg}

            ### INSTRUCTIONS
            1. Analyse la DEMANDE_UTILISATEUR en tenant compte de la DERNIÈRE_RÉPONSE.
            2. Si la demande implique une **amélioration / reformulation / plus de détails** de la DERNIÈRE_RÉPONSE :
               – Réécris ou complète cette réponse de façon plus claire et précise, sans répéter inutilement.
            3. Si la demande est un **résumé** :
               – Produit un résumé concis, structuré, en évitant la simple paraphrase phrase-par-phrase.
            4. Si la demande est de **poser X questions** :
               – Génère EXACTEMENT X QCM clairs, chacune avec 4 choix (A, B, C, D) et la bonne réponse indiquée.
            5. Si le nombre de questions n’est pas précisé :
               – Demande « Combien de questions souhaitez-vous ? » et rien d’autre.
            6. Réponds toujours dans un style pédagogique, fluide, sans préambule superflu.
        """)

    # ──────────────────────────────────────────────────────────────
    # PUBLIC
    def answer(
        self,
        question: str,
        context: str = "",
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> str:
        """Appelle le LLM avec prompt enrichi."""
        # Récupère la toute dernière réponse pour ce user/conversation
        last = self.memory.get_last_response(user_id or "", conversation_id)
        last_answer = last.get("response", "") if last else ""

        prompt = self._build_prompt(question, context, last_answer)

        try:
            response = self.llm.invoke(prompt).content.strip()

            # Sauvegarde dans la mémoire d’agent
            if user_id:
                self.memory.save_response(
                    user_id=user_id,
                    conversation_id=conversation_id or "",
                    query=question,
                    response=response,
                    metadata={"context": context}
                )
            return response

        except Exception as e:
            _LOG.error("Erreur LLM PDF Agent : %s", e)
            return f"Erreur : {e}"

    def run(
        self,
        user_input: Optional[str] = None,
        user_message: Optional[str] = None,
        raw_text: Optional[str] = None,
        pdf_content: Optional[str] = None,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> str:
        """Point d’entrée externe : choisit message + contexte et appelle `answer`."""
        message  = user_input or user_message or ""
        context  = pdf_content or raw_text or ""
        return self.answer(message, context, user_id, conversation_id)
