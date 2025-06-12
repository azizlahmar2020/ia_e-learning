import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from features.cours_management.prompts.prompt_suggestion import suggestion_prompt_template
from features.cours_management.tools import suggestion_tools
import re

load_dotenv()

class SuggestionAgent:
    def __init__(self):
        self.llm = ChatGroq(
            model_name="llama3-8b-8192",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.7
        )

    def suggest(self, user_id: str) -> list:
        role = suggestion_tools.get_user_role.invoke(user_id)
        history = suggestion_tools.get_user_memories.invoke(user_id)

        interests = ""
        if role.lower() == "student":
            interests = suggestion_tools.get_user_interests.invoke(user_id)
            print("🎯 INTERESTS FETCHED:", interests)

        prompt = suggestion_prompt_template.format(
            user_role=role,
            interests=interests,
            history=history
        )

        response = self.llm.invoke(prompt)

        try:
            parsed = extract_first_json_block(response.content)
            return parsed.get("suggestions", [])
        except Exception as e:
            print("❌ JSON parsing failed:", e)
            print("🪵 RAW content:", response.content)
            return []


def extract_first_json_block(text: str):
    """Extract the first JSON object from the LLM response."""
    match = re.search(r"\{[\s\S]*?\}", text.strip())
    if match:
        return json.loads(match.group())
    else:
        raise ValueError("No valid JSON block found in LLM response")