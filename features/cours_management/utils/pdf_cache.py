"""
Gestionnaire de cache PDF thread-safe avec TTL.
Ce module fournit une classe pour stocker et récupérer des fichiers PDF
avec une gestion de durée de vie et de synchronisation.
"""

import threading
import time
from typing import Dict, Any, Optional, Tuple


class PDFCache:
    """
    Gestionnaire de cache PDF thread-safe avec TTL.
    Permet de stocker temporairement des PDF et de les récupérer
    avec une gestion de la durée de vie et des accès concurrents.
    """

    def __init__(self, ttl_seconds: int = 900):  # 15 minutes par défaut
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._ttl_seconds = ttl_seconds

    def _create_key(self, user_id: str, conv_id: Optional[str] = None) -> str:
        """
        Crée une clé standardisée pour le cache.

        Args:
            user_id: Identifiant de l'utilisateur
            conv_id: Identifiant de conversation, peut être None

        Returns:
            Clé standardisée au format "user_id:conversation_id" ou "user_id:*"
        """
        return f"{user_id}:{conv_id or '*'}"

    def store(self, user_id: str, pdf_bytes: bytes,
              conv_id: Optional[str] = None, pending: bool = False) -> None:
        """
        Stocke un PDF dans le cache avec horodatage.

        Args:
            user_id: Identifiant de l'utilisateur
            pdf_bytes: Contenu binaire du PDF
            conv_id: Identifiant de conversation, peut être None
            pending: Indique si le PDF est en attente de traitement
        """
        with self._lock:
            timestamp = time.time()
            # Clé spécifique
            specific_key = self._create_key(user_id, conv_id)
            self._cache[specific_key] = {
                "pdf": pdf_bytes,
                "ts": timestamp,
                "pending": pending
            }

            # Clé générique (fallback)
            generic_key = self._create_key(user_id)
            self._cache[generic_key] = {
                "pdf": pdf_bytes,
                "ts": timestamp,
                "pending": pending
            }

    def retrieve(self, user_id: str, conv_id: Optional[str] = None) -> Tuple[Optional[bytes], bool, Optional[str]]:
        """
        Récupère un PDF du cache avec vérification TTL.

        Args:
            user_id: Identifiant de l'utilisateur
            conv_id: Identifiant de conversation, peut être None

        Returns:
            Tuple (pdf_bytes, pending, key_hit) où:
            - pdf_bytes: Contenu binaire du PDF ou None si non trouvé
            - pending: Indique si le PDF est en attente de traitement
            - key_hit: Clé utilisée pour récupérer le PDF ou None si non trouvé
        """
        with self._lock:
            # Essayer d'abord la clé spécifique
            specific_key = self._create_key(user_id, conv_id)
            result = self._get_entry(specific_key)
            if result[0]:
                return result

            # Essayer ensuite la clé générique
            generic_key = self._create_key(user_id)
            return self._get_entry(generic_key)

    def _get_entry(self, key: str) -> Tuple[Optional[bytes], bool, Optional[str]]:
        """
        Récupère une entrée du cache avec vérification TTL.

        Args:
            key: Clé de l'entrée à récupérer

        Returns:
            Tuple (pdf_bytes, pending, key) ou (None, False, None) si non trouvé ou expiré
        """
        entry = self._cache.get(key)
        if not entry:
            return None, False, None

        # Vérifier si l'entrée a expiré
        if time.time() - entry["ts"] > self._ttl_seconds:
            self._cache.pop(key, None)
            return None, False, None

        return entry["pdf"], entry["pending"], key

    def update_status(self, key: str, pending: bool) -> bool:
        """
        Met à jour le statut d'une entrée du cache.

        Args:
            key: Clé de l'entrée à mettre à jour
            pending: Nouveau statut pending

        Returns:
            True si la mise à jour a réussi, False sinon
        """
        with self._lock:
            if key not in self._cache:
                return False

            self._cache[key]["pending"] = pending
            return True

    def clear_expired(self) -> int:
        """
        Nettoie les entrées expirées du cache.

        Returns:
            Nombre d'entrées supprimées
        """
        with self._lock:
            now = time.time()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now - entry["ts"] > self._ttl_seconds
            ]

            for key in expired_keys:
                self._cache.pop(key, None)

            return len(expired_keys)
