"""
Utilitaires pour la gestion des accès concurrents et l'isolation des états des agents.
Ce module fournit des classes pour gérer les ressources partagées et isoler
les états des agents de manière thread-safe.
"""

import threading
from typing import Dict, Any, Optional, Callable, TypeVar, Generic

T = TypeVar('T')


class ResourceLock(Generic[T]):
    """
    Gestionnaire de verrou pour ressources partagées avec contexte.
    Permet d'accéder à une ressource de manière thread-safe en utilisant
    le pattern context manager (with).
    """

    def __init__(self, resource: T):
        self.resource = resource
        self.lock = threading.RLock()

    def __enter__(self):
        self.lock.acquire()
        return self.resource

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.lock.release()


class AgentStateManager:
    """
    Gestionnaire d'état isolé pour chaque agent.
    Permet de maintenir des états séparés pour chaque agent et conversation,
    évitant ainsi les interférences entre agents.
    """

    def __init__(self):
        self._states: Dict[str, Dict[str, Any]] = {}
        self._locks: Dict[str, threading.RLock] = {}
        self._global_lock = threading.RLock()

    def get_state(self, agent_id: str, conversation_id: str) -> Dict[str, Any]:
        """
        Récupère l'état isolé d'un agent pour une conversation spécifique.

        Args:
            agent_id: Identifiant de l'agent
            conversation_id: Identifiant de la conversation

        Returns:
            État isolé de l'agent pour cette conversation
        """
        key = f"{agent_id}:{conversation_id}"
        with self._global_lock:
            if key not in self._states:
                self._states[key] = {}
            if key not in self._locks:
                self._locks[key] = threading.RLock()
        return self._states[key]

    def with_state(self, agent_id: str, conversation_id: str) -> ResourceLock[Dict[str, Any]]:
        """
        Accède à l'état d'un agent de manière thread-safe.

        Args:
            agent_id: Identifiant de l'agent
            conversation_id: Identifiant de la conversation

        Returns:
            ResourceLock contenant l'état de l'agent
        """
        key = f"{agent_id}:{conversation_id}"
        with self._global_lock:
            if key not in self._states:
                self._states[key] = {}
            if key not in self._locks:
                self._locks[key] = threading.RLock()
        return ResourceLock(self._states[key])

    def clear_state(self, agent_id: str, conversation_id: str) -> None:
        """
        Efface l'état d'un agent pour une conversation spécifique.

        Args:
            agent_id: Identifiant de l'agent
            conversation_id: Identifiant de la conversation
        """
        key = f"{agent_id}:{conversation_id}"
        with self._global_lock:
            if key in self._states:
                del self._states[key]
            if key in self._locks:
                del self._locks[key]
