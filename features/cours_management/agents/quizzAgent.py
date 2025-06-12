import os
import json
import logging
import re
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import AIMessage
from langchain.chains import LLMChain
from features.cours_management.prompts.cours_prompt import build_operation_prompt
from features.common.websocket_manager import send_progress


class QuizAgent:
    def __init__(self):
        load_dotenv()
        self.llm = ChatGroq(
            model_name="llama3-8b-8192",
            api_key=os.getenv("GROQ_API_KEY"),
            temperature=0
        )
        self.prompt, self.parser = build_operation_prompt()
        self.chain = self.prompt | self.llm

    async def generate_quiz_for_chapters_async(self, course_id: int, chapters: list) -> list:
        """
        Génère un quiz JSON pour chaque chapitre du cours.
        """
        all_quizzes = []

        for idx, chapter in enumerate(chapters):
            # Récupération des informations du chapitre en tenant compte des différentes casse possibles
            chapter_id = chapter.get("CHAPTER_ID") or chapter.get("chapter_id")
            chapter_title = chapter.get("TITLE") or chapter.get("title")
            chapter_content = chapter.get("CONTENT") or chapter.get("content")

            prompt = f"""
Tu es un générateur de quiz pour une plateforme e-learning.
Génère un quiz structuré en JSON pour le chapitre suivant :
rendre uniquement un json pas d'autre message
Titre : {chapter_title}
Contenu : {chapter_content}

Format attendu :
{{
  "questions": [
    {{
      "question_id": 1,
      "question_text": "...",
      "question_type": "MULTIPLE_CHOICE_SINGLE",
      "answers": [
        {{"answer_id": 1, "answer_text": "...", "is_correct": false}},
        {{"answer_id": 2, "answer_text": "...", "is_correct": true}}
      ]
    }}
  ]
}}
            """.strip()

            try:
                await send_progress(f"📝 Generating quiz {idx + 1}...")
                response = self.llm.invoke(prompt)
                print(f"📩 [LLM RESPONSE] →\n{response.content[:500]}...\n")

                # On cherche le premier '{' pour localiser le début de l'objet JSON
                start_json = response.content.find("{")
                quiz_json = response.content[start_json:] if start_json >= 0 else response.content

                if not quiz_json.strip().startswith("{"):
                    raise ValueError(f"Réponse invalide (pas de JSON) : {quiz_json[:100]}")

                # Utilisation du raw_decode pour extraire l'objet JSON et ignorer les données supplémentaires
                try:
                    decoder = json.JSONDecoder()
                    quiz_data, idx = decoder.raw_decode(quiz_json)
                except Exception as e:
                    await send_progress(f"❌ Failed to create quiz {idx + 1}: {str(e)}")
                    continue
                quiz_record = {
                    "course_id": course_id,
                    "chapter_id": chapter_id,
                    "title": f"Quiz - {chapter_title}",
                    "description": f"Auto-generated quiz for chapter: {chapter_title}",
                    "status": "Draft",
                    "content": quiz_data
                }

                all_quizzes.append(quiz_record)
                await send_progress(f"✅ Quiz {idx + 1} created: {quiz_record['title']}")

            except Exception as e:
                await send_progress(f"❌ Failed to create quiz {idx + 1}: {str(e)}")


        return all_quizzes

    def generate_quiz_operation(self, course_id: int, chapters: list):
        quizzes = self.generate_quiz_for_chapters(course_id, chapters)
        return {
            "operation": "save_generated_quizzes",
            "parameters": quizzes
        }
