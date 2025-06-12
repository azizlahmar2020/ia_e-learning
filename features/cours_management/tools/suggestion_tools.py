import requests
from langchain_core.tools import tool

BASE_URL = "https://apex.oracle.com/pls/apex/naxxum/elearning/"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Content-Type": "application/json; charset=utf-8"
}
TIMEOUT = 15

@tool("get_user_role")
def get_user_role(user_id: str) -> str:
    """Retourne le rôle de l'utilisateur (Student, Professor, etc.) à partir de l'ID."""
    try:
        url = f"{BASE_URL}userRole/{user_id}"
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT).json()
        return res.get("user_role", "Unknown")
        print(res)
    except Exception as e:
        print("❌ get_user_role error:", e)
        return "Unknown"

@tool("get_user_interests")
def get_user_interests(user_id: str) -> str:
    """Retourne les intérêts d’un étudiant donné par son ID."""
    try:
        url = f"{BASE_URL}student_interests/{user_id}"
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT).json()
        return res.get("interests", "")
    except Exception as e:
        print("❌ get_user_interests error:", e)
        return ""

@tool("get_user_memories")
def get_user_memories(user_id: str) -> str:
    """Retourne l’historique des messages précédents d’un utilisateur sous forme de texte brut."""
    try:
        url = f"{BASE_URL}suggestion_memo/{user_id}"
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT).json()
        print(res)
        return "\n".join([item["raw_text"] for item in res.get("items", [])])
    except Exception as e:
        print("❌ get_user_memories error:", e)
        return ""
