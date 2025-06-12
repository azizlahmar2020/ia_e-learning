import logging
import os
import json
from typing import List, Dict
import re

from PyPDF2 import PdfReader, errors as pdf_errors
import io
from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langchain_groq import ChatGroq
from langchain.chains import LLMChain
from features.cours_management.prompts.cours_prompt import build_operation_prompt
from features.cours_management.tools.course_qa_tools import answer_about_course

class CourseAgent:
    def __init__(self):
        load_dotenv()

        self.llm = ChatGroq(
            model_name="llama3-8b-8192",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.2
        )

        self.prompt, self.parser = build_operation_prompt()

        self.chain = self.prompt | self.llm

    def detect_operation(self, user_input: str, history: str = "", memories: str = "", pdf_bytes: bytes = None) -> dict:
        if pdf_bytes:
            return {
                "operation": "process_pdf",
                "parameters": {"pdf_bytes": pdf_bytes}
            }
        try:
            # Ajoute le rag_context (memories) dans l'input du LLM
            inputs = {
                "input": user_input,
                "history": history,
                "memories": memories  # rag_context ici
            }
            response = self.chain.invoke(inputs)
            logging.debug("Response from detect operation LLM: %s", response)
            text = response.content if hasattr(response, "content") else response["text"]

            # Extraction stricte du JSON
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                json_text = match.group(0)
            else:
                json_text = text  # fallback

            output = self.parser.parse(json_text)
            if "parameters" in output and isinstance(output["parameters"], dict):
                output["parameters"] = {
                    k: v for k, v in output["parameters"].items()
                    if v not in [None, "", 0, [], {}]
                }
            if not isinstance(output, dict) or "operation" not in output:
                return self._fallback("Format JSON invalide")

            logging.debug("Operation detected: %s", output["operation"])
            return output

        except json.JSONDecodeError:
            return self._fallback("Erreur de parsing JSON")
        except Exception as e:
            return self._fallback(e.__str__())

    def process_pdf(self, pdf_bytes: bytes):
        try:
            with io.BytesIO(pdf_bytes) as pdf_stream:
                pdf_reader = PdfReader(pdf_stream)

                # Extraire le texte brut
                full_text = "\n".join([page.extract_text() for page in pdf_reader.pages])

                # Utiliser LLM pour structurer le contenu
                structured_response = self.chain.invoke({
                    "input": f"Structure le contenu suivant en chapitres de cours. Conserve exactement tout le contenu du PDF, ni plus ni moins, et dans la langue originale, sans ajouter d'exemples ou d'informations supplémentaires :\n{full_text}",
                    "history": "",
                    "memories": ""
                })

                start_json = structured_response.content.find("{")
                formatted_response = AIMessage(content=structured_response.content[
                                                       start_json:] if start_json >= 0 else structured_response.content)
                output = self.parser.parse(formatted_response.content)

            return output

        except Exception as e:
            return {"error": f"PDF processing error: {str(e)}"}

    def generate_pdf_suggestions(self, user_role: str = "public") -> str:
        """
        Utilise le LLM pour proposer des actions pertinentes sur le PDF
        et répond **dans la langue de l’utilisateur déduite du contexte**.
        """
        prompt = f"""
   Tu es un assistant e-learning.
L'utilisateur a envoyé un document PDF sans message.
Son rôle est : {user_role}.
Commence par "Bonjour, que souhaitez-vous faire avec ce PDF ?", sans poser de question réelle.
Ensuite, propose trois actions possibles, adaptées à son rôle.
Exprime-toi dans la langue des messages précédents (déduis la langue).
Chaque action doit être formulée en une phrase courte (15 mots max), sans code, sans balises, sans format JSON, sans question.

Suggestions disponibles :

instructor :

Générer un résumé du document

Créer un cours basé sur le PDF

Extraire les points clés pour un cours

Créer un quiz à partir du contenu

Analyser le contenu du document

student :

Générer un quiz de préparation

Expliquer le contenu du document

Créer un résumé du document

M’aider à comprendre les concepts difficiles

Répondre à mes questions sur ce PDF
    """
        response = self.llm.invoke(prompt).content.strip()
        return response
    def answer_about_memories(self, memories: List[Dict], question: str):
        """Analyse les souvenirs pour générer une réponse textuelle à une question libre."""
        # Cherche les messages qui indiquent un cours terminé
        cours = []
        for m in memories:
            for msg in m.get("messages", []):
                if "j'ai terminé le cours" in msg.get("content", "").lower():
                    titre = msg.get("content").split(":", 1)[-1].strip()
                    cours.append(titre)
        if not cours:
            return {"response": "Vous n'avez pas encore terminé de cours."}
        return {"response": "Voici vos anciens cours :\n" + "\n".join(cours)}

    def answer_course_question(self, question: str, course_title: str = "") -> dict:
        try:
            answer = answer_about_course.invoke({"question": question, "course_title": course_title})
            return {
                "operation": "response",
                "parameters": {"response": answer}
            }
        except Exception as e:
            return {
                "operation": "response",
                "parameters": {"response": f"Erreur lors de la réponse sur le cours: {str(e)}"}
            }

    def _fallback(self, message: str) -> dict:
        return {
            "operation": "fallback_response",
            "parameters": {"response": message}
        }
