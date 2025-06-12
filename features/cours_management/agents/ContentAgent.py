import os
import json
import re
from dotenv import load_dotenv
from langchain_groq import ChatGroq


class ContentAgent:
    def __init__(self):
        load_dotenv()
        self.llm = ChatGroq(
            model_name="llama3-8b-8192",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0.3  # Réduit pour plus de cohérence
        )

    def generate_content_for_chapter(self, chapter: dict) -> dict:
        title = chapter.get("title", "Untitled Chapter")
        instructions = chapter.get("content", "")

        prompt = f"""
        GÉNÈRE un chapitre e-learning en JSON STRICT.
        TITRE: {title}
        INSTRUCTIONS: {instructions}
        FORMAT REQUIS:
        {{
          "Title": "{title}",
          "Content": "<h2>...</h2><p>...</p>"
        }}
        """

        response = self.llm.invoke(prompt)
        return self.robust_json_parser(response.content, title)

    def robust_json_parser(self, raw_text: str, fallback_title: str) -> dict:
        # Nettoyage initial
        clean_text = re.sub(r'^```json|```$', '', raw_text, flags=re.MULTILINE).strip()

        # Tentative de parsing standard
        try:
            return json.loads(clean_text)
        except json.JSONDecodeError:
            pass

        # Fallback 1: Extraction de champs
        json_data = {
            "Title": fallback_title,
            "Content": self.extract_html_content(clean_text)
        }

        # Fallback 2: Regex avancé
        title_match = re.search(r'"Title"\s*:\s*"((?:\\"|[^"])*)"', clean_text)
        content_match = re.search(r'"Content"\s*:\s*"((?:\\"|[^"]|\\\n)*)"', clean_text, re.DOTALL)

        if title_match:
            json_data["Title"] = json.loads(f'"{title_match.group(1)}"')
        if content_match:
            json_data["Content"] = json.loads(f'"{content_match.group(1)}"')

        return json_data

    def extract_html_content(self, text: str) -> str:
        # Détection de contenu HTML valide
        html_content = re.findall(r'(<[^>]+>.*<\/[^>]+>)', text, re.DOTALL)
        return html_content[0] if html_content else "<p>Contenu non généré</p>"