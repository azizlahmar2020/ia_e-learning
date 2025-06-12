import logging
from typing import Optional, Dict, Any

import requests
from langchain.tools import tool
from pydantic import BaseModel, Field, Extra

from core.config import BASE_URL, API_ENDPOINTS

logging.basicConfig(filename="debug.log", level=logging.DEBUG)

import json

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Content-Type": "application/json; charset=utf-8"
}
TIMEOUT = 15


class UpdateUserInput(BaseModel):
    user_id: int = Field(..., description="ID de l'utilisateur à mettre à jour")

    class Config:
        extra = Extra.allow


class UserTools:
    def __init__(self, user_role: str):
        self.user_role = user_role

    def _check_admin_access(self):
        if self.user_role != "Admin":
            return {"error": "Access denied. Only administrators can perform this action."}
        return None

    @tool("get_users")
    def get_users(filter: Optional[Dict[str, Any]] = None, user_role: str = "Public"):
        """Récupère la liste des utilisateurs avec des filtres facultatifs."""
        # Check if user has admin access
        if user_role != "Admin":
            return "Access denied. Only administrators can view all users."

        try:
            response = requests.get(
                BASE_URL + 'elearning/' + 'users',
                params=filter or {},
                headers=HEADERS,
                timeout=TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    @tool("get_user_by_id")
    def get_user_by_id(user_id: int, user_role: str = "Public"):
        """Récupère un utilisateur spécifique par son ID."""
        if not isinstance(user_id, int):
            return {"error": "user_id doit être un entier"}

        # Check if user has admin access or is requesting their own profile
        current_user = None
        if user_role != "Admin" and (not current_user or current_user.user_id != user_id):
            return "Access denied. You can only view your own profile."

        try:
            url = BASE_URL + API_ENDPOINTS["Users"]["GET_BY_ID"].format(user_id=user_id)
            response = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    @tool("create_user")
    def create_user(user: Dict[str, Any], user_role: str = "Public"):
        """Crée un nouvel utilisateur."""
        # Check if user has admin access
        if user_role != "Admin":
            return "Access denied. Only administrators can create users."

        try:
            response = requests.post(
                BASE_URL + API_ENDPOINTS["Users"]["POST"],
                json=user,
                headers=HEADERS,
                timeout=TIMEOUT
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    @tool("update_user", args_schema=UpdateUserInput)
    def update_user(**user_data: Dict[str, Any]) -> dict[str, str] | dict[str, str] | str | Any:
        """Met à jour un utilisateur existant avec les champs fournis."""
        user_role = user_data.get('user_role', 'Public')
        user_id = user_data.get('user_id')

        # Check if user has admin access or is updating their own profile
        current_user = None  # You would need to get this from the session
        if user_role != "Admin" and (not current_user or current_user.user_id != user_id):
            return "Access denied. You can only update your own profile."

        try:
            if not user_id:
                return {"error": "Le paramètre 'user_id' est requis"}

            data_to_update = user_data.copy()
            data_to_update.pop('user_id', None)
            data_to_update.pop('user_role', None)

            url = BASE_URL + 'elearning/' + API_ENDPOINTS["Users"]["PUT"].format(user_id=user_id)
            response = requests.put(
                url,
                json=data_to_update,
                headers=HEADERS,
                timeout=TIMEOUT
            )
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    @tool("delete_user")
    def delete_user(user_id: int, user_role: str = "Public"):
        """Supprime un utilisateur."""
        # Check if user has admin access
        if user_role != "Admin":
            return "Access denied. Only administrators can delete users."

        try:
            url = f"{BASE_URL}elearning/User/{user_id}"
            print(f"🔗 URL de suppression : {url}")

            delete_headers = {
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json"
            }

            response = requests.delete(url, headers=delete_headers, timeout=15)

            # Nettoyage et parsing de la réponse
            try:
                clean_response = response.text.strip().replace('\n', '')  # Supprime les sauts de ligne
                response_data = json.loads(clean_response)  # Convertit en JSON
                apex_message = response_data.get("X-APEX-STATUS-MESSAGE", "Pas de message")
            except json.JSONDecodeError:
                apex_message = "Réponse invalide de l'API"

            # Formatage final
            if response.status_code == 200 and "deleted" in apex_message.lower():
                return {
                    "status": "success",
                    "message": apex_message.replace('"', '')
                }
            else:
                return {
                    "error": apex_message.replace('"', ''),
                    "status_code": response.status_code
                }

        except Exception as e:
            return {"error": f"Erreur critique : {str(e)}"}
