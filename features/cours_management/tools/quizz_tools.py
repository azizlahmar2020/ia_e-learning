from typing import List, Dict
from pydantic import BaseModel, Field
from langchain.tools import tool
import requests
import json
import re
from features.common.websocket_manager import send_progress
import asyncio


class QuizCreationSchema(BaseModel):
    quizzes: List[Dict] = Field(..., description="Liste de quizzes à insérer")


class QuizTools:

    @staticmethod
    @tool("save_generated_quizzes", args_schema=QuizCreationSchema)
    def save_generated_quizzes(quizzes: List[Dict]):
        """
        Envoie chaque quiz généré à l'API REST APEX, attend une réponse JSON contenant success + quiz_id.
        Cette version corrige l'erreur "Extra data" en essayant d'extraire le premier objet JSON
        si la réponse contient des données supplémentaires.
        """
        results = []
        print("Quizzes to send:", quizzes)
        for quiz in quizzes:
            try:
                # Champs requis
                required_keys = ['course_id', 'chapter_id', 'title', 'content']
                if not all(k in quiz for k in required_keys):
                    results.append({
                        "error": "Champs requis manquants",
                        "quiz": quiz
                    })
                    continue

                # Payload pour l'API
                payload = {
                    "course_id": quiz["course_id"],
                    "chapter_id": quiz["chapter_id"],
                    "title": quiz["title"],
                    "description": quiz.get("description", ""),
                    "status": quiz.get("status", "Draft"),
                    "content": quiz["content"]
                }

                # Appel API
                response = requests.post(
                    "https://apex.oracle.com/pls/apex/naxxum/elearning/quizz",
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0"
                    },
                    timeout=20
                )

                raw_text = response.text.strip()
                print("Raw response text:", raw_text)


                # Cas succès
                if response.status_code == 201:
                    try:
                        data = response.json()
                    except Exception as e:
                        if "Extra data" in str(e):
                            match = re.search(r'(\{.*?\})', raw_text, re.DOTALL)
                            if match:
                                try:
                                    data = json.loads(match.group(1))
                                except Exception as e2:
                                    results.append({"error": f"Erreur JSON après correction: {str(e2)}"})
                                    continue
                            else:
                                results.append({"error": f"Aucun objet JSON valide trouvé dans la réponse: {str(e)}"})
                                continue
                        else:
                            results.append({"error": f"Erreur parsing JSON: {str(e)}"})
                            continue

                    results.append({
                        "status": "created",
                        "quiz_id": data.get("quiz_id"),
                        "message": data.get("message")
                    })

                else:
                    results.append({
                        "error": "Échec API",
                        "status_code": response.status_code,
                        "response": raw_text
                    })

            except Exception as e:
                results.append({"error": f"Erreur système : {str(e)}"})

        return {"results": results}