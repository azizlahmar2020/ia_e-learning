# features/cours_management/memory_course/conversation_memory.py
# ──────────────────────────────────────────────────────────────────
import logging, uuid, threading
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse

from langchain_core.messages import (
    HumanMessage, AIMessage, SystemMessage, BaseMessage
)

# ────────────────────────────── CONFIG
_MAX_ASSISTANT_CHARS = 800  # tronque la réponse enregistrée
_COLLECTION_NAME = "conversation_memory"
_VECTOR_DUMMY = [0.0]
_MAX_CONTEXT_LENGTH = 3000  # limite de taille pour le contexte

log = logging.getLogger(__name__)


# ────────────────────────────── CLASS
class ConversationMemory:
    """
    •  Sauvegarde <user_msg, assistant_msg_truncated, meta>
    •  Récupère les N dernières entrées (avec filtrage éventuel sur conversation_id)
    •  Version améliorée avec synchronisation thread-safe et réconciliation
    """

    def __init__(self,
                 collection_name: str = _COLLECTION_NAME,
                 host: str = "localhost",
                 port: int = 6333):

        self.collection_name = collection_name
        self.client = None
        self.is_available = False
        self.local_memory: Dict[str, list] = {}
        self._lock = threading.RLock()  # Verrou réentrant pour la synchronisation
        self._last_sync_attempt = datetime.min
        self._sync_interval = timedelta(minutes=5)

        try:
            self.client = QdrantClient(host, port=port)
            self._create_collection_if_needed()
            self.is_available = True
            log.info("Qdrant OK sur %s:%s", host, port)
        except (ResponseHandlingException, UnexpectedResponse, ConnectionError) as e:
            log.warning("Qdrant KO (%s) → mode local only", e)

    # ───────────────────── INTERNAL
    def _create_collection_if_needed(self):
        if not self.client:
            return
        coll = self.client.get_collections().collections
        if any(c.name == self.collection_name for c in coll):
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=models.VectorParams(size=1, distance=models.Distance.COSINE)
        )
        log.info("Collection %s créée", self.collection_name)

    # ───────────────────── PUBLIC API
    # ── save_conversation ──────────────────────────────────────────────────────
    def save_conversation(
            self,
            user_id: str,
            user_message: str = "",
            assistant_message: str = "",
            conversation_id: Optional[str] = None,
            meta: Optional[Dict[str, Any]] = None,
            system_message: Optional[str] = None
    ) -> bool:
        """
        Enregistre un échange (au moins un des deux messages peut être vide).
        Version thread-safe avec tentative de synchronisation périodique.
        Supporte l'ajout d'un message système pour enrichir le contexte.
        """
        if not user_id or (not user_message and not assistant_message and not system_message):
            log.warning("save_conversation: nothing to save")
            return False

        with self._lock:
            # Construit la liste « messages » dynamiquement avec rôles explicites
            messages: list[dict[str, str]] = []

            # Ajouter le message système en premier s'il existe
            if system_message:
                messages.append({"role": "system", "content": system_message[:_MAX_CONTEXT_LENGTH]})

            if user_message:
                messages.append({"role": "user", "content": user_message})

            if assistant_message:
                # on tronque SEULEMENT si non vide
                assistant_trim = assistant_message[:_MAX_ASSISTANT_CHARS]
                messages.append({"role": "assistant", "content": assistant_trim})

            payload = {
                "user_id": str(user_id),
                "conversation_id": str(conversation_id or ""),
                "messages": messages,
                "timestamp": datetime.now().isoformat(),
            }
            if meta:
                payload.update(meta)

            # fallback local
            if not self.is_available or not self.client:
                self.local_memory.setdefault(user_id, []).append(payload)
                return True

            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=[models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=_VECTOR_DUMMY,
                        payload=payload
                    )]
                )

                # Tentative de synchronisation périodique
                self._try_sync_local_memory()

                return True
            except Exception as e:
                log.error("Upsert Qdrant failed → local (%s)", e)
                self.local_memory.setdefault(user_id, []).append(payload)
                return True

    def _try_sync_local_memory(self):
        """Tente de synchroniser la mémoire locale avec Qdrant périodiquement."""
        now = datetime.now()
        if not self.is_available or not self.client:
            return

        if now - self._last_sync_attempt < self._sync_interval:
            return

        self._last_sync_attempt = now

        try:
            # Synchroniser les entrées locales avec Qdrant
            for user_id, entries in self.local_memory.items():
                if not entries:
                    continue

                points = []
                for entry in entries:
                    points.append(models.PointStruct(
                        id=str(uuid.uuid4()),
                        vector=_VECTOR_DUMMY,
                        payload=entry
                    ))

                if points:
                    self.client.upsert(
                        collection_name=self.collection_name,
                        points=points
                    )

            # Vider la mémoire locale après synchronisation réussie
            self.local_memory.clear()
            log.info("Synchronisation de la mémoire locale vers Qdrant réussie")
        except Exception as e:
            log.error("Échec de la synchronisation avec Qdrant: %s", e)

    # ----------------------- READ
    def get_recent_conversations(
            self,
            user_id: str,
            conversation_id: Optional[str] = None,
            limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        Récupère les conversations récentes pour un utilisateur et une conversation.
        Version thread-safe avec gestion améliorée des fallbacks.
        """
        with self._lock:
            # …
            must = []
            if user_id:
                must.append(models.FieldCondition(
                    key="user_id", match=models.MatchValue(value=str(user_id))
                ))
            if conversation_id:
                must.append(models.FieldCondition(
                    key="conversation_id", match=models.MatchValue(value=str(conversation_id))
                ))

            # ---------- helper interne ---------------------------------------
            def _local_fetch() -> List[Dict[str, Any]]:
                mem = self.local_memory.get(user_id, [])
                return sorted(mem, key=lambda x: x["timestamp"], reverse=True)[:limit]

            # -----------------------------------------------------------------

            # ----- Mode dégradé (pas de Qdrant) ------------------------------
            if not self.is_available or not self.client:
                return _local_fetch()

            # ----- 1ᵉʳ essai : avec conversation_id (si fourni) --------------
            must = [models.FieldCondition(
                key="user_id",
                match=models.MatchValue(value=user_id)
            )]
            if conversation_id:
                must.append(models.FieldCondition(
                    key="conversation_id",
                    match=models.MatchValue(value=conversation_id)
                ))

            try:
                points, _ = self.client.scroll(
                    collection_name=self.collection_name,
                    scroll_filter=models.Filter(must=must),
                    limit=limit,
                    with_payload=True,
                    with_vectors=False,
                )
                convs = [p.payload for p in points]
                if convs:  # ✅ trouvé
                    return sorted(convs,
                                  key=lambda x: x.get("timestamp", ""),
                                  reverse=True)[:limit]

                # ----- Repli : filtre uniquement sur user_id -----------------
                if conversation_id:  # (on avait demandé un ID)
                    points, _ = self.client.scroll(
                        collection_name=self.collection_name,
                        scroll_filter=models.Filter(must=must[:1]),  # user_id seul
                        limit=limit,
                        with_payload=True,
                        with_vectors=False,
                    )
                    convs = [p.payload for p in points]
                    if convs:
                        return sorted(convs,
                                      key=lambda x: x.get("timestamp", ""),
                                      reverse=True)[:limit]

            except Exception as e:
                log.error("Scroll error (%s) → local fallback", e)

            # ----- Si tout échoue : mémoire locale ---------------------------
            return _local_fetch()

    # ----------------------- RECONSTRUCT
    @staticmethod
    def reconstruct_messages(conversations: List[Dict[str, Any]],
                             max_length: int = _MAX_CONTEXT_LENGTH) -> List[BaseMessage]:
        """
        Transforme la liste JSON ↦ objets LangChain.
        Respecte la limite de taille du contexte et structure les rôles explicitement.
        """
        chain_msgs: List[BaseMessage] = []
        total_length = 0

        # Traiter les conversations dans l'ordre chronologique inverse (plus récentes d'abord)
        for conv in sorted(conversations, key=lambda x: x.get("timestamp", ""), reverse=True):
            conv_msgs = []
            # Traiter les messages dans l'ordre chronologique
            for msg in conv.get("messages", []):
                txt = msg.get("content", "")
                if not txt:
                    continue

                role = msg.get("role")
                if role == "user":
                    conv_msgs.append(HumanMessage(content=txt))
                elif role == "assistant":
                    conv_msgs.append(AIMessage(content=txt))
                elif role == "system":
                    conv_msgs.append(SystemMessage(content=txt))

                total_length += len(txt)

            # Ajouter les messages de cette conversation
            chain_msgs.extend(conv_msgs)

            # Vérifier si on a atteint la limite de taille
            if total_length >= max_length:
                log.info(f"Limite de contexte atteinte ({total_length}/{max_length}), troncature appliquée")
                break

        return chain_msgs
