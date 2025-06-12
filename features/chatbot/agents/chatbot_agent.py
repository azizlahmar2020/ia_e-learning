import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.chains import LLMChain
from features.chatbot.prompts.chatbot_prompt import build_chat_prompt


class ChatbotAgent:
    def __init__(self):
        load_dotenv()

        self.llm = ChatGroq(
            model_name="llama3-8b-8192",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.7
        )

        self.prompt = build_chat_prompt()

        self.chain = LLMChain(
            llm=self.llm,
            prompt=self.prompt,
            verbose=True
        )

    def get_response(self, message: str) -> str:
        """Get a conversational response from the chatbot."""
        try:
            response = self.chain.invoke({"input": message})
            return response.strip() if isinstance(response, str) else response.get("text", "").strip()

        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}"
