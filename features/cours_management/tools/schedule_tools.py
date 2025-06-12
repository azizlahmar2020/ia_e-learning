import requests
import os
from typing import Optional, Dict, Any
import urllib          # ✅ ajoute ce import
import urllib.parse     # (garde l’accès à urllib.parse.urlencode)
class ScheduleTools:

    @staticmethod
    def create_session(data: dict):
        """
        Prépare la session pour validation manuelle
        """
        # Validation des données requises
        required_fields = ["instructor_id", "room_name", "title", "start_time", "end_time"]
        if not all(field in data for field in required_fields):
            return {"error": "Champs obligatoires manquants"}

        return {
            "validation_required": True,
            "operation": "schedule_session",
            "session_data": data
        }

    @staticmethod
    def validate_session(data: dict):

        try:
            print (data)
            response = requests.post(
                "https://apex.oracle.com/pls/apex/naxxum/live_sessions/",
                json=data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0"
                },
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Erreur d'API: {str(e)}")
            return {"error": f"Échec de la création de session: {str(e)}"}

    @staticmethod
    def query_sessions(params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recherche dynamique + filtre local : tri par start_time / end_time et limite.
        """
        # Extraire les paramètres de tri
        date_type = params.pop("P_DATE_TYPE", "START")
        order = params.pop("P_ORDER_BY", "ASC")
        raw_limit = params.pop("P_LIMIT", None)

        # 🔐 Sécuriser le cast de LIMIT
        limit = int(raw_limit) if raw_limit not in (None, "", "null") else 0
        date_type = str(date_type).upper()
        order = str(order).upper()

        # Nettoyer les autres paramètres pour l'URL
        clean = {k: v for k, v in params.items() if v not in (None, "", "null")}
        qs = urllib.parse.urlencode(clean, quote_via=urllib.parse.quote)
        url = f"https://apex.oracle.com/pls/apex/naxxum/elearning/searchlivesessiondynamic?{qs}" if qs else \
            "https://apex.oracle.com/pls/apex/naxxum/elearning/searchlivesessiondynamic"

        try:
            resp = requests.get(url, headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0"
            }, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            sessions = data.get("items", data)

            # 🧠 Tri local
            key = "start_time" if date_type == "START" else "end_time"
            sessions_sorted = sorted(
                sessions,
                key=lambda x: x.get(key) or "",
                reverse=(order == "DESC")
            )

            if limit > 0:
                sessions_sorted = sessions_sorted[:limit]

            msg = "Voici les sessions trouvées." if sessions_sorted else "Aucune session ne correspond à votre recherche."
            return {"sessions": sessions_sorted, "message": msg}

        except requests.exceptions.RequestException as exc:
            return {"sessions": [], "message": f"Erreur API : {exc}"}
