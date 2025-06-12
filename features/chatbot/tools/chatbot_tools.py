from datetime import datetime
from langchain_core.tools import Tool
from features.chatbot.agents.chatbot_agent import ChatbotAgent


class ChatbotTools:
    def __init__(self):
        self.chatbot_agent = ChatbotAgent()

        self.chat_tool = Tool(
            name="chat",
            description="Gère les conversations générales avec l'utilisateur",
            func=self.handle_chat
        )

    def handle_chat(self, input_data) -> str:
        """
        Gère les requêtes de type dict ou str. Fonctionne même si input est mal formé.
        """
        try:
            if isinstance(input_data, dict):
                message  = input_data.get("input", "")
                history = input_data.get("history", "")
                if history:
                    message = f"{history}\n\nUtilisateur : {message}"
            elif isinstance(input_data, str):
                message = input_data
            else:
                return "❌ Mauvais format pour le message."

            return self.chatbot_agent.get_response(message)
        except Exception as e:
            return f"❌ Erreur dans handle_chat: {str(e)}"

    def get_date(self) -> str:
        return datetime.now().date().isoformat()

    def get_time(self) -> str:
        return datetime.now().time().isoformat()
