import json
import os
import logging
from dotenv import load_dotenv

from typing import Dict, Any
from langchain_groq import ChatGroq
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate
)

class DetectionAgent:
    def __init__(self, model_name: str = "llama3-8b-8192", temperature: float = 0.3):
        """
        Initialise l'agent avec un modèle de langage.
        """
        self.llm = ChatGroq(
            model_name=model_name,
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=temperature
        )

        # Définir le prompt système
        self.system_prompt = SystemMessagePromptTemplate.from_template(
            """You are an intent detection assistant for an E-learning chatbot.
            Your task is to analyze user messages and map them to specific operations.

            Available operations:
            - get_courses: For listing/viewing courses (e.g., "show courses", "list courses", "display courses")
            - create_course: For creating new courses (e.g., "I want to add a new course", "create a course")
            - update_course: For modifying existing courses (e.g., "edit course", "update course details")
            - delete_course: For removing courses (e.g., "delete this course", "remove a course")
            - get_course_by_id: For viewing specific course details (e.g., "show course details for ID 123")
            - schedule_session: For scheduling live sessions (e.g., "schedule a session", "plan a live class")
            - process_pdf: For handling PDF course uploads (e.g., "upload this PDF", "add a course from PDF")
            - chat: For general conversation (use as last resort)

            Return a JSON object with:
            - operation: The detected operation
            - parameters: Any relevant parameters
            - confidence: A number between 0 and 1 indicating confidence in the detection.

            IMPORTANT:
            - Always analyze the context and user role before deciding the operation.
            - If the intent is unclear, return "chat" as the operation with a low confidence score."""
        )

        # Définir le prompt utilisateur
        self.human_prompt = HumanMessagePromptTemplate.from_template(
            "User role: {role}\n"
            "Last message: {message}\n"
            "History context: {history}\n"
            "Memories: {memories}\n"
            "Has PDF: {has_pdf}\n"
            "\nAnalyze the intent and respond with the JSON for the operation."
        )

        # Combiner les prompts
        self.prompt = ChatPromptTemplate.from_messages([
            self.system_prompt,
            self.human_prompt
        ])

    def detect_operation(self, role: str, message: str, history: str = "", memories: str = "", has_pdf: bool = False) -> Dict[str, Any]:
        """
        Utilise le modèle de langage pour détecter l'opération à partir du message utilisateur.
        """
        # Formater le prompt
        formatted_prompt = self.prompt.format_prompt(
            role=role,
            message=message,
            history=history,
            memories=memories,
            has_pdf=str(has_pdf)
        )

        # Appeler le modèle de langage
        response = self.llm.invoke(formatted_prompt.to_messages())

        # Loguer la réponse brute pour déboguer
        logging.info(f"LLM Response: {response.content}")

        try:
            # Tenter de parser la réponse en JSON
            data = json.loads(response.content)

            # Valider la structure de la réponse
            if not isinstance(data, dict) or "operation" not in data:
                logging.warning("Invalid response structure, falling back to chat.")
                return self._fallback(message)

            # Ajouter des valeurs par défaut si nécessaire
            data.setdefault("confidence", 0.8)
            data.setdefault("parameters", {})
            data["parameters"]["user_role"] = role

            return data

        except json.JSONDecodeError:
            # En cas d'erreur, retourner une réponse par défaut
            logging.error("Failed to parse LLM response, falling back to chat.")
            return self._fallback(message)

    def _fallback(self, message: str) -> Dict[str, Any]:
        """
        Fallback en cas d'échec de détection.
        """
        return {
            "operation": "chat",
            "parameters": {
                "input": message,
                "clarification_needed": True,
                "clarification_message": "Je n'ai pas compris votre demande. Pouvez-vous reformuler ou préciser ce que vous voulez faire ?"
            },
            "confidence": 0.5
        }