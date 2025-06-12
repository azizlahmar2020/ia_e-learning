"""
Utilitaires pour la gestion des identifiants de conversation.
Ce module fournit des fonctions pour normaliser et manipuler les identifiants
de conversation de manière cohérente dans tout le système.
"""

import uuid
from typing import Optional, Tuple


def normalize_conversation_id(conv_id: Optional[str]) -> str:
    """
    Normalise un identifiant de conversation, en générant un nouveau si nécessaire.

    Args:
        conv_id: Identifiant de conversation à normaliser, peut être None

    Returns:
        Identifiant de conversation normalisé (jamais None ou vide)
    """
    if not conv_id or not conv_id.strip():
        return str(uuid.uuid4())
    return str(conv_id).strip()


def create_conversation_key(user_id: str, conv_id: Optional[str]) -> str:
    """
    Crée une clé de conversation standardisée combinant user_id et conversation_id.

    Args:
        user_id: Identifiant de l'utilisateur
        conv_id: Identifiant de conversation, peut être None

    Returns:
        Clé de conversation standardisée au format "user_id:conversation_id"
    """
    normalized_conv_id = normalize_conversation_id(conv_id)
    return f"{user_id}:{normalized_conv_id}"


def create_fallback_key(user_id: str) -> str:
    """
    Crée une clé de fallback standardisée pour un utilisateur.

    Args:
        user_id: Identifiant de l'utilisateur

    Returns:
        Clé de fallback au format "user_id:*"
    """
    return f"{user_id}:*"


def parse_conversation_key(key: str) -> Tuple[str, str]:
    """
    Extrait user_id et conversation_id d'une clé de conversation.

    Args:
        key: Clé de conversation au format "user_id:conversation_id"

    Returns:
        Tuple (user_id, conversation_id)
    """
    parts = key.split(":", 1)
    if len(parts) != 2:
        return key, ""
    return parts[0], parts[1]
