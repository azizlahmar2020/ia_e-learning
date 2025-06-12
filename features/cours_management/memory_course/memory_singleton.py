# Nouveau fichier: features/cours_management/memory_course/memory_singleton.py
from typing import Optional
from features.cours_management.memory_course.conversation_memory import ConversationMemory
from features.cours_management.rag.qdrant_rag import QdrantRAG


class MemorySingleton:
    _conversation_memory_instance: Optional[ConversationMemory] = None
    _qdrant_rag_instance: Optional[QdrantRAG] = None

    @classmethod
    def get_conversation_memory(cls, collection_name="conversation_memory") -> ConversationMemory:
        if cls._conversation_memory_instance is None:
            try:
                cls._conversation_memory_instance = ConversationMemory(collection_name=collection_name)
            except Exception:
                cls._conversation_memory_instance = ConversationMemory(collection_name=f"{collection_name}_backup")
        return cls._conversation_memory_instance

    @classmethod
    def get_qdrant_rag(cls, collection_name="course_knowledge") -> QdrantRAG:
        if cls._qdrant_rag_instance is None:
            try:
                cls._qdrant_rag_instance = QdrantRAG(collection_name=collection_name)
            except Exception:
                cls._qdrant_rag_instance = QdrantRAG(collection_name=f"{collection_name}_backup")
        return cls._qdrant_rag_instance
