from datetime import datetime
from fastapi import Depends
import requests
from typing import Optional, Dict, Any
from langchain.tools import tool
from core.config import BASE_URL, API_ENDPOINTS
import logging
import json
from features.common.websocket_manager import send_progress
import httpx
from features.cours_management.rag.qdrant_rag import QdrantRAG

from features.cours_management.agents.quizzAgent import QuizAgent
from features.cours_management.tools.quizz_tools import QuizTools
from features.cours_management.agents.TestAgent import TestAgent
from features.user_management.api import get_current_user

logging.basicConfig(filename="debug.log", level=logging.DEBUG)

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Content-Type": "application/json; charset=utf-8"
}
TIMEOUT = 15

save_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
qdrant_rag = QdrantRAG()

class CourseTools:

    @staticmethod
    @tool("get_courses")
    def get_courses(filters: Optional[Dict[str, Any]] = None):
        """Récupère la liste des cours avec leurs chapitres."""
        try:
            response = requests.get(
                BASE_URL + API_ENDPOINTS["Courses"]["GET"],
                params=filters or {},
                headers=HEADERS,
                timeout=TIMEOUT
            )
            response.raise_for_status()

            course_data = response.json()
            courses = course_data.get("items") or course_data.get("data") or course_data

            if not isinstance(courses, list):
                return {"error": "Format de réponse inattendu pour les cours"}

            for course in courses:
                course_id = course.get("course_id") or course.get("id")
                if not course_id:
                    continue
                try:
                    chapter_resp = requests.get(
                        f"{BASE_URL}/elearning/chapter/{course_id}",
                        headers=HEADERS,
                        timeout=TIMEOUT
                    )
                    if chapter_resp.status_code == 200:
                        course["chapters"] = chapter_resp.json().get("items", [])
                    else:
                        course["chapters"] = []
                except Exception:
                    course["chapters"] = []

            result = {"success": True, "data": courses}
            return result
        except requests.RequestException as e:
            return {"error": str(e)}

    @staticmethod
    async def create_course(course_data: Dict[str, Any]) -> Dict[str, Any]:
        user_id = str(course_data.get("user_id") or "anonymous")
        await send_progress("📘 Creating course…")

        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                # 1️⃣ Créer le cours
                response = await client.post(
                    BASE_URL + "elearning/course",
                    json=course_data,
                    headers=HEADERS
                )
                response.raise_for_status()
                response_data = response.json()
                course_id = response_data.get("course_id") or response_data.get("COURSE_ID")

                await send_progress(f"✅ Course created (ID: {course_id})")
                await send_progress("📚 Fetching chapters...")

                # 2️⃣ Récupérer les chapitres
                chapter_resp = await client.get(
                    f"{BASE_URL}elearning/chapterbycourse/{course_id}",
                    headers=HEADERS
                )
                raw = chapter_resp.json()
                chapters_items = raw.get("items", [])
                chapters_with_content = []
                for ch in chapters_items:
                    ch_id = ch.get("chapter_id")
                    content_resp = await client.get(
                        f"{BASE_URL}elearning/contentbychapter/{ch_id}",
                        headers=HEADERS
                    )
                    data = content_resp.json()
                    items = data.get("items", [])
                    body = items[0].get("content", "") if items else ""
                    chapters_with_content.append({
                        "chapter_id": ch_id,
                        "title": ch.get("title", ""),
                        "content": body
                    })

            await send_progress("🧠 Starting quiz generation...")

            # 3️⃣ Générer les quiz
            quiz_agent = QuizAgent()
            quizzes = await quiz_agent.generate_quiz_for_chapters_async(course_id, chapters_with_content)
            if quizzes:
                QuizTools.save_generated_quizzes.invoke({"quizzes": quizzes})

            # 4️⃣ Générer l'examen
            test_agent = TestAgent()
            exam_data = await test_agent.create_exam_async({
                **course_data,
                "course_id": course_id,
                "chapters": chapters_with_content,
                "quizzes": quizzes
            })

            if exam_data.get("error"):
                raise RuntimeError(f"Échec génération examen : {exam_data['details']}")

            for key in ("title", "status", "content"):
                if not exam_data.get(key):
                    raise RuntimeError(f"Champ manquant dans l'examen : {key}")

            # 5️⃣ Enregistrer l'examen
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                test_response = await client.post(
                    f"{BASE_URL}elearning/test",
                    json={
                        "course_id": course_id,
                        "title": exam_data["title"],
                        "description": exam_data["description"],
                        "status": exam_data["status"],
                        "content": exam_data["content"]
                    },
                    headers=HEADERS
                )

                if test_response.status_code != 201:
                    logging.warning("⚠️ Échec enregistrement du test")
                else:
                    logging.info("✅ Test enregistré")

            return {
                "success": True,
                "data": response_data,
                "course_id": course_id,
                "chapters": chapters_with_content,
                "quizzes": quizzes,
                "exam": exam_data
            }

        except httpx.TimeoutException:
            return {"error": "Timeout: serveur lent"}
        except httpx.HTTPStatusError as e:
            return {"error": "Erreur HTTP", "details": str(e)}
        except Exception as e:
            logging.exception("Erreur système")
            return {"error": f"Erreur critique : {str(e)}"}


    @staticmethod
    @tool("update_course")
    def update_course(course_id: int, update_data: Dict[str, Any]):
        """Met à jour un cours existant."""
        #current_user = None  # You would need to get this from the session
        #if user_role != "Admin" and (not current_user or current_user.user_id != user_id):
         #   return "Access denied. You can only update your own profile."
        try:
            url = BASE_URL + API_ENDPOINTS["Courses"]["PUT"].format(course_id=course_id)
            response = requests.put(
                url,
                json=update_data,
                headers=HEADERS,
                timeout=TIMEOUT
            )
            response.raise_for_status()
            result = response.json()
            return result
        except requests.RequestException as e:
            return {"error": str(e)}

    @staticmethod
    @tool("get_course_by_id")
    def get_course_by_id(course_id: int) -> Dict[str, Any]:
        """Récupère un cours spécifique par son identifiant."""
        try:
            url = BASE_URL + API_ENDPOINTS["Courses"]["GET_BY_ID"].format(course_id=course_id)
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            response.raise_for_status()

            response_data = response.json()
            data = response_data.get("items", response_data)

            result = None
            if isinstance(data, list) and len(data) > 0:
                result = {"success": True, "data": data[0], "course_id": course_id}
            elif isinstance(data, dict):
                result = {"success": True, "data": data, "course_id": course_id}
            else:
                return {"error": "Aucun cours trouvé avec cet ID", "course_id": course_id}

            return result
        except requests.RequestException as e:
            return {"error": str(e)}
        except Exception as e:
            return {"error": f"Erreur système: {str(e)}"}

    @staticmethod
    @tool("delete_course")
    def delete_course(course_id: int):
        """Supprime un cours avec gestion du format de réponse Oracle APEX."""
        try:
            url = f"{BASE_URL}elearning/Course/{course_id}"
            print(f"🔗 URL de suppression : {url}")
            delete_headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
            response = requests.delete(url, headers=delete_headers, timeout=15)
            try:
                clean_response = response.text.strip().replace('\n', '')
                response_data = json.loads(clean_response)
                apex_message = response_data.get("X-APEX-STATUS-MESSAGE", "Pas de message")
            except json.JSONDecodeError:
                apex_message = "Réponse invalide de l'API"
            if response.status_code == 200 and "deleted" in apex_message.lower():
                result = {
                    "status": "success",
                    "message": apex_message.replace('"', ''),
                    "course_id": course_id
                }
                return result
            else:
                return {
                    "error": apex_message.replace('"', ''),
                    "status_code": response.status_code
                }
        except Exception as e:
            return {"error": f"Erreur critique : {str(e)}"}

    @staticmethod
    @tool("search_courses_advanced")
    def search_courses_advanced(
            title: Optional[str] = None,
            tags: Optional[str] = None,
            language: Optional[str] = None,
            min_price: Optional[float] = None,
            max_price: Optional[float] = None,
            status: Optional[str] = None,
            target_audience: Optional[str] = None
    ):
        """
        Recherche avancée des cours avec filtres : title, tags, language, min_price, max_price, status, target_audience
        """
        filters = {
            "title": title,
            "tags": tags,
            "language": language,
            "min_price": min_price,
            "max_price": max_price,
            "status": status,
            "target_audience": target_audience
        }
        filters = {k: v for k, v in filters.items() if v is not None}

        try:
            logging.info(f"✅ Filtres transmis à l'API : {filters}")
            url = f"{BASE_URL}elearning/courses"
            response = requests.get(url, params=filters, headers=HEADERS, timeout=TIMEOUT)

            if not response.ok:
                return {
                    "error": f"Erreur API : {response.status_code}",
                    "raw_response": response.text[:200]
                }

            course_data = response.json()
            courses = course_data.get("items") or course_data.get("data") or course_data



            # Traitement des cours
            for course in courses:
                course_id = course.get("course_id") or course.get("id")
                if not course_id:
                    continue

                try:
                    chapter_resp = requests.get(
                        f"{BASE_URL}/elearning/chapter/{course_id}",
                        headers=HEADERS,
                        timeout=TIMEOUT
                    )
                    if chapter_resp.status_code == 200:
                        course["chapters"] = chapter_resp.json().get("items", [])
                    else:
                        course["chapters"] = []
                except Exception:
                    course["chapters"] = []

            return {"success": True, "data": courses}

        except requests.RequestException as e:
            return {"error": str(e)}


    @staticmethod
    @tool("fallback_response")
    def fallback_response(response: str):
        """Gère les demandes non comprises."""
        result = {"error": response}
        return result