import json
import os

from dotenv import load_dotenv
from langchain.chains import LLMChain
from langchain_groq import ChatGroq

from features.user_management.prompts.user_prompt import build_operation_prompt


def _fallback(message: str) -> dict:
    return {
        "operation": "fallback_response",
        "parameters": {"response": f"Erreur: {message}"}
    }


class UserAgent:
    def __init__(self):
        load_dotenv()

        self.llm = ChatGroq(
            model_name="llama3-8b-8192",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0
        )

        self.prompt, self.parser = build_operation_prompt()

        self.llm = ChatGroq(
            model_name="llama3-8b-8192",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.2
        )

    def detect_operation(self, user_input: str) -> dict:
        try:
            response = self.chain.invoke({"input": user_input})
            print("🔍 Réponse brute du modèle :", response)

            output = self.parser.parse(response["text"])

            if not isinstance(output, dict) or "operation" not in output:
                return _fallback("Format JSON invalide")

            if output["operation"] == "get_user_by_id" and "user" in output["parameters"]:
                output["parameters"]["user_id"] = output["parameters"]["user"].get("user_id")

            print("✅ Opération détectée :", output)
            return output

        except json.JSONDecodeError:
            return _fallback("Erreur de parsing JSON")
        except Exception as e:
            return _fallback(str(e))
