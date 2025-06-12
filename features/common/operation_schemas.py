# ─── ROUTER CONSTANTS ──────────────────────────────────────────────────────────
SYSTEM_PROMPT = (
    "Tu es un routeur d’opérations pour un chatbot e-learning. "
    "Analyse le message utilisateur + le contexte et choisis UNE seule fonction "
    "parmi celles ci-dessous. Réponds exclusivement par un appel de fonction JSON."
)

FUNCTION_SCHEMAS = [
    {
        "name": "show_calendar",
        "description": "Afficher le calendrier de l’utilisateur.",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "answer_about_course",
        "description": "Répondre à une question sur un cours via RAG Qdrant.",
        "parameters": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "Question posée par l’utilisateur"
                },
                "course_title": {
                    "type": "string",
                    "description": "Titre du cours concerné (facultatif)"
                }
            },
            "required": ["question"]
        }
    },
    {
        "name": "process_pdf",
        "description": "Importer un cours depuis un PDF fourni par un instructeur.",
        "parameters": {
            "type": "object",
            "properties": {
                "pdf_bytes": {
                    "type": "string",
                    "description": "Contenu binaire du PDF encodé en base64"
                }
            },
            "required": ["pdf_bytes"]
        }
    },
    {
        "name": "schedule_session",
        "description": "Créer ou requêter des sessions live.",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["create", "query"],
                    "description": "Créer une nouvelle session ou consulter les sessions existantes"
                },
                "instructor_id": {
                    "type": "integer",
                    "description": "ID de l’instructeur (requis pour create)"
                },
                "room_name": {
                    "type": "string",
                    "description": "Nom de la salle (requis pour create)"
                },
                "title": {
                    "type": "string",
                    "description": "Titre de la session (requis pour create)"
                },
                "start_time": {
                    "type": "string",
                    "description": "Date/heure de début ISO 8601 (requis pour create)"
                },
                "end_time": {
                    "type": "string",
                    "description": "Date/heure de fin ISO 8601 (requis pour create)"
                },
                "filters": {
                    "type": "object",
                    "description": "Filtres pour la requête de sessions (query)",
                    "properties": {
                        "P_INSTRUCTOR_ID":   {"type": ["integer","null"]},
                        "P_ROOM_NAME":       {"type": ["string","null"]},
                        "P_COURSE_TITLE":    {"type": ["string","null"]},
                        "P_START_DATE_FROM": {"type": ["string","null"]},
                        "P_START_DATE_TO":   {"type": ["string","null"]},
                        "P_TIME_FROM":       {"type": ["string","null"]},
                        "P_TIME_TO":         {"type": ["string","null"]},
                        "P_DATE_TYPE":       {"type": ["string","null"], "enum":["START","END"]},
                        "P_ORDER_BY":        {"type": ["string","null"], "enum":["ASC","DESC"]},
                        "P_LIMIT":           {"type": ["integer","null"]}
                    }
                }
            },
            "required": ["action"]
        }
    },
    {
        "name": "get_course_by_id",
        "description": "Récupérer un cours par son ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "course_id": {
                    "type": "integer",
                    "description": "Identifiant du cours à récupérer."
                }
            },
            "required": ["course_id"]
        }
    },
    {
        "name": "get_courses",
        "description": "Lister tous les cours disponibles (avec filtres optionnels).",
        "parameters": {
            "type": "object",
            "properties": {
                "title":          {"type": ["string","null"]},
                "tags":           {"type": ["string","null"]},
                "language":       {"type": ["string","null"]},
                "min_price":      {"type": ["number","null"]},
                "max_price":      {"type": ["number","null"]},
                "status":         {"type": ["string","null"]},
                "target_audience":{"type": ["string","null"]}
            }
        }
    },
    {
        "name": "create_course",
        "description": "Créer un nouveau cours avec les données fournies.",
        "parameters": {
            "type": "object",
            "properties": {
                "course_data": {
                    "type": "object",
                    "description": "Objet complet du cours à créer (voir documentation)."
                }
            },
            "required": ["course_data"]
        }
    },
    {
        "name": "update_course",
        "description": "Mettre à jour un cours existant.",
        "parameters": {
            "type": "object",
            "properties": {
                "course_id":    {"type": "integer"},
                "update_data":  {"type": "object"}
            },
            "required": ["course_id","update_data"]
        }
    },
    {
        "name": "delete_course",
        "description": "Supprimer un cours existant.",
        "parameters": {
            "type": "object",
            "properties": {
                "course_id": {"type": "integer"}
            },
            "required": ["course_id"]
        }
    },
    {
        "name": "search_courses_advanced",
        "description": "Recherche avancée des cours avec filtres multiples.",
        "parameters": {
            "type": "object",
            "properties": {
                "title":           {"type": ["string","null"]},
                "tags":            {"type": ["string","null"]},
                "language":        {"type": ["string","null"]},
                "min_price":       {"type": ["number","null"]},
                "max_price":       {"type": ["number","null"]},
                "status":          {"type": ["string","null"]},
                "target_audience": {"type": ["string","null"]}
            }
        }
    },
    {
        "name": "save_generated_quizzes",
        "description": "Enregistrer les quiz générés via l’API APEX.",
        "parameters": {
            "type": "object",
            "properties": {
                "quizzes": {
                    "type": "array",
                    "items": {"type":"object"},
                    "description": "Liste des quizzes à insérer"
                }
            },
            "required": ["quizzes"]
        }
    },
    {
        "name": "fallback_response",
        "description": "Gérer les demandes non comprises par un message simple.",
        "parameters": {
            "type": "object",
            "properties": {
                "response": {"type":"string"}
            },
            "required": ["response"]
        }
    },
    {
        "name": "chat",
        "description": "Répondre en langage naturel si aucune autre fonction ne convient.",
        "parameters": {
            "type": "object",
            "properties": {
                "input": {"type":"string"}
            },
            "required": ["input"]
        }
    }
]
# ───────────────────────────────────────────────────────────────────────────────
