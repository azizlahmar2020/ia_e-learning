from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema

def build_test_prompt():
    # 🧠 Message système : définition claire
    system_message = """
Tu es un générateur d’examen intelligent pour une plateforme e-learning.

🎯 Objectif :
Génère exactement 10 questions à choix multiple (QCM) pour un examen final à partir :
- du contenu d’un cours (titre, langue, audience, prérequis…)
- de ses chapitres
- des quizzes générés précédemment
- Pas de duplication des questions du quiz.

📌 Format strict à retourner :
{{
  "course_id": ...,
  "title": "...",
  "description": "...",
  "status": "Draft",
  "content": {{
    "questions": [
      {{
        "question_text": "...",
        "question_type": "MULTIPLE_CHOICE_SINGLE",
        "answers": [
          {{ "answer_text": "...", "is_correct": true }},
          {{ "answer_text": "...", "is_correct": false }},
          ...
        ]
      }},
      ...
    ]
  }}
}}
 


⚠️ Règles obligatoires :
- toujours rendre un json correct, sans aucun texte hors JSON
- Pas de duplication des questions du quiz.
- Retourne **exactement 10 questions**
- Chaque question contient **4 réponses maximum**
- Une seule réponse correcte (`"is_correct": true`)
- **Le champ** `"course_id"` **doit être toujours présent et égal à** `{{course_data.course_id}}`
- **Le champ** `"title"` **doit commencer par** `"Test - {{course_data.title}}"`
- Le champ `"status"` est toujours `"Draft"`
"""

    response_schemas = [
        ResponseSchema(name="course_id", description="ID du cours concerné"),
        ResponseSchema(name="title", description="Titre du test"),
        ResponseSchema(name="description", description="Description du test"),
        ResponseSchema(name="status", description="Statut ('Draft')"),
        ResponseSchema(name="content", description="Liste de 10 questions")
    ]
    parser = StructuredOutputParser.from_response_schemas(response_schemas)

    # On récupère les instructions de format (avec {…}) et on les échappe
    format_instructions = parser.get_format_instructions()
    # Échapper les accolades pour qu’elles soient littérales
    format_instructions = format_instructions.replace("{", "{{").replace("}", "}}")

    full_system = system_message + "\n\n" + format_instructions

    prompt = ChatPromptTemplate.from_messages([
        ("system", full_system),
        ("human", "{course_data}")
    ])
    return prompt, parser