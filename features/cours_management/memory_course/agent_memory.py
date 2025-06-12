"""
Module de gestion de la mémoire spécifique aux agents.
Ce module permet de suivre et d'analyser les réponses générées par chaque agent
pour améliorer la personnalisation et la pertinence des futures interactions.
"""

import logging
import threading
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from features.cours_management.memory_course.memory_singleton import MemorySingleton

logger = logging.getLogger(__name__)


class AgentMemory:
    """
    Classe pour gérer la mémoire spécifique à chaque agent.
    Permet de stocker et d'analyser les réponses générées pour améliorer
    les futures interactions.
    """

    def __init__(self, agent_type: str):
        """
        Initialise la mémoire pour un type d'agent spécifique.

        Args:
            agent_type: Type d'agent (summarize, qa, pdf_suggestion, etc.)
        """
        self.agent_type = agent_type
        self.conversation_memory = MemorySingleton.get_conversation_memory()
        self._lock = threading.RLock()
        self._local_cache: Dict[str, List[Dict[str, Any]]] = {}

    def save_response(self,
                      user_id: str,
                      conversation_id: str,
                      query: str,
                      response: str,
                      metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Enregistre une réponse générée par l'agent avec métadonnées.

        Args:
            user_id: Identifiant de l'utilisateur
            conversation_id: Identifiant de la conversation
            query: Requête de l'utilisateur
            response: Réponse générée par l'agent
            metadata: Métadonnées supplémentaires (paramètres, contexte, etc.)

        Returns:
            True si l'enregistrement a réussi, False sinon
        """
        if not user_id or not response:
            logger.warning(f"{self.agent_type}_memory: nothing to save")
            return False

        with self._lock:
            # Préparer les données à sauvegarder
            payload = {
                "agent_type": self.agent_type,
                "user_id": str(user_id),
                "conversation_id": str(conversation_id or ""),
                "query": query,
                "response": response,
                "timestamp": datetime.now().isoformat(),
            }

            if metadata:
                payload["metadata"] = metadata

            # Sauvegarder dans la mémoire de conversation principale
            # avec un tag spécial pour identifier les réponses d'agent
            meta = {
                "agent_type": self.agent_type,
                "agent_memory": True
            }
            if metadata:
                meta.update(metadata)

            # Sauvegarder dans le cache local pour un accès rapide
            cache_key = f"{user_id}:{conversation_id}"
            if cache_key not in self._local_cache:
                self._local_cache[cache_key] = []
            self._local_cache[cache_key].append(payload)

            # Sauvegarder dans la mémoire de conversation
            return self.conversation_memory.save_conversation(
                user_id=user_id,
                user_message=query,
                assistant_message=response,
                conversation_id=conversation_id,
                meta=meta
            )

    def get_recent_responses(self,
                             user_id: str,
                             conversation_id: Optional[str] = None,
                             limit: int = 5) -> List[Dict[str, Any]]:
        """
        Récupère les réponses récentes générées par cet agent.

        Args:
            user_id: Identifiant de l'utilisateur
            conversation_id: Identifiant de la conversation (optionnel)
            limit: Nombre maximum de réponses à récupérer

        Returns:
            Liste des réponses récentes avec leurs métadonnées
        """
        with self._lock:
            # Vérifier d'abord le cache local
            if conversation_id:
                cache_key = f"{user_id}:{conversation_id}"
                if cache_key in self._local_cache:
                    return sorted(
                        self._local_cache[cache_key],
                        key=lambda x: x.get("timestamp", ""),
                        reverse=True
                    )[:limit]

            # Récupérer depuis la mémoire de conversation
            conversations = self.conversation_memory.get_recent_conversations(
                user_id=user_id,
                conversation_id=conversation_id,
                limit=limit * 2  # Récupérer plus pour filtrer ensuite
            )

            # Filtrer pour ne garder que les réponses de cet agent
            agent_responses = []
            for conv in conversations:
                meta = conv.get("meta", {})
                if meta.get("agent_type") == self.agent_type and meta.get("agent_memory"):
                    # Reconstruire la structure de réponse
                    messages = conv.get("messages", [])
                    user_msg = next((m.get("content", "") for m in messages if m.get("role") == "user"), "")
                    assistant_msg = next((m.get("content", "") for m in messages if m.get("role") == "assistant"), "")

                    response = {
                        "agent_type": self.agent_type,
                        "user_id": conv.get("user_id", ""),
                        "conversation_id": conv.get("conversation_id", ""),
                        "query": user_msg,
                        "response": assistant_msg,
                        "timestamp": conv.get("timestamp", ""),
                    }

                    # Ajouter les métadonnées si présentes
                    if "metadata" in meta:
                        response["metadata"] = meta["metadata"]

                    agent_responses.append(response)

            return sorted(
                agent_responses,
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )[:limit]

    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Analyse les interactions passées pour déterminer les préférences de l'utilisateur.
        Utilisé pour enrichir le contexte système avec des informations personnalisées.

        Args:
            user_id: Identifiant de l'utilisateur

        Returns:
            Dictionnaire des préférences détectées
        """
        # Récupérer toutes les réponses récentes pour cet utilisateur
        responses = self.get_recent_responses(user_id, limit=10)

        # Initialiser les préférences par défaut
        preferences = {
            "format_preference": "default",
            "detail_level": "medium",
            "language": "fr",
            "topics_of_interest": [],
            "interaction_history": []
        }

        # Analyser les réponses pour détecter les préférences
        if not responses:
            return preferences

        # Exemple d'analyse simple (à personnaliser selon les besoins)
        topics = {}
        formats = {"bullet": 0, "paragraph": 0, "detailed": 0, "concise": 0}

        # Collecter les interactions récentes pour le contexte
        recent_interactions = []

        for resp in responses:
            # Analyser le format des réponses
            response_text = resp.get("response", "")
            query_text = resp.get("query", "")

            # Ajouter à l'historique d'interaction pour le contexte
            if query_text and response_text:
                recent_interactions.append({
                    "query": query_text,
                    "response_summary": response_text[:100] + "..." if len(response_text) > 100 else response_text
                })

            if "•" in response_text or "-" in response_text:
                formats["bullet"] += 1
            else:
                formats["paragraph"] += 1

            if len(response_text) > 500:
                formats["detailed"] += 1
            else:
                formats["concise"] += 1

            # Analyser les métadonnées pour les sujets d'intérêt
            metadata = resp.get("metadata", {})
            if "topics" in metadata:
                for topic in metadata["topics"]:
                    topics[topic] = topics.get(topic, 0) + 1

        # Déterminer les préférences basées sur l'analyse
        if formats["bullet"] > formats["paragraph"]:
            preferences["format_preference"] = "bullet"
        else:
            preferences["format_preference"] = "paragraph"

        if formats["detailed"] > formats["concise"]:
            preferences["detail_level"] = "high"
        else:
            preferences["detail_level"] = "low"

        # Déterminer les sujets d'intérêt (top 3)
        preferences["topics_of_interest"] = sorted(
            topics.items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]

        # Ajouter les interactions récentes (limitées aux 5 dernières)
        preferences["interaction_history"] = recent_interactions[:5]

        return preferences
    def get_last_response(self, user_id: str, conversation_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Récupère la dernière réponse enregistrée par l'agent pour un utilisateur donné.

        Args:
            user_id: Identifiant de l'utilisateur
            conversation_id: ID de la conversation (optionnel)

        Returns:
            La dernière réponse enregistrée ou None
        """
        recent = self.get_recent_responses(user_id, conversation_id, limit=1)
        return recent[0] if recent else None

    def clear_cache(self):
        """Vide le cache local."""
        with self._lock:
            self._local_cache.clear()
