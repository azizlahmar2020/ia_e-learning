import logging
from typing import Dict, List, Any, Optional, Tuple
from langchain_core.messages import HumanMessage
from features.cours_management.rag.qdrant_rag import QdrantRAG


class RAGAgent:
    def __init__(self, host="localhost", port=6333):
        # Configuration du logger
        self.logger = logging.getLogger(__name__)

        # Initialisation du RAG avec gestion d'erreur
        try:
            self.rag = QdrantRAG(host=host, port=port)
            self.is_available = self.rag.is_available
            self.logger.info("RAGAgent initialisé avec succès")
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation du RAGAgent: {str(e)}")
            self.rag = None
            self.is_available = False

    def process_query(self, query: str, history_context: str = "", k: int = 3) -> Dict[str, Any]:
        """Traite une requête utilisateur avec RAG"""
        # Vérification des entrées
        if not query or not query.strip():
            self.logger.warning("Requête vide, retour d'un contexte vide")
            return {
                "enriched_context": "",
                "documents": []
            }

        # Normalisation de k
        k = max(1, min(k, 10))  # Limiter k entre 1 et 10

        # Vérification de la disponibilité du RAG
        if not self.rag or not self.rag.is_available:
            self.logger.warning("RAG non disponible, retour d'un contexte vide")
            return {
                "enriched_context": "",
                "documents": []
            }

        try:
            # Recherche des documents pertinents
            relevant_docs = self.rag.search(query, k=k)

            # Si aucun document n'est trouvé
            if not relevant_docs:
                self.logger.info(f"Aucun document pertinent trouvé pour la requête: {query}")
                return {
                    "enriched_context": "",
                    "documents": []
                }

            # Construction du contexte enrichi
            context = ""
            for i, doc in enumerate(relevant_docs):
                if not hasattr(doc, 'page_content'):
                    continue

                context += f"Document {i + 1}:\n{doc.page_content}\n\n"

                # Ajout des métadonnées pertinentes
                if hasattr(doc, 'metadata') and doc.metadata:
                    context += f"Source: {doc.metadata.get('title', 'Unknown')}\n"
                    if 'course_id' in doc.metadata:
                        context += f"Course ID: {doc.metadata['course_id']}\n"

            # Retourne le contexte enrichi et les documents
            return {
                "enriched_context": context,
                "documents": relevant_docs
            }
        except Exception as e:
            self.logger.error(f"Erreur lors du traitement de la requête RAG: {str(e)}")
            return {
                "enriched_context": "",
                "documents": [],
                "error": str(e)
            }

    def search_with_score(self, query: str, k: int = 3) -> List[Tuple[Dict[str, Any], float]]:
        """Recherche des documents pertinents avec scores de similarité et formatage simplifié"""
        if not query or not query.strip():
            self.logger.warning("Requête vide, retour d'une liste vide")
            return []

        # Normalisation de k
        k = max(1, min(k, 10))  # Limiter k entre 1 et 10

        # Vérification de la disponibilité du RAG
        if not self.rag or not self.rag.is_available:
            self.logger.warning("RAG non disponible, retour d'une liste vide")
            return []

        try:
            # Recherche avec score
            results = self.rag.search_with_score(query, k=k)

            # Formatage des résultats
            formatted_results = []
            for doc, score in results:
                if not hasattr(doc, 'page_content') or not hasattr(doc, 'metadata'):
                    continue

                formatted_results.append(({
                                              "content": doc.page_content,
                                              "metadata": doc.metadata
                                          }, score))

            return formatted_results
        except Exception as e:
            self.logger.error(f"Erreur lors de la recherche avec score: {str(e)}")
            return []

    def detect_operation(self, user_input: str, history: str = "", memories: str = "") -> Dict[str, Any]:
        """Détecte l'opération à effectuer et enrichit avec RAG si nécessaire"""
        if not user_input or not user_input.strip():
            return {
                "operation": "chat",
                "parameters": {
                    "input": user_input or "",
                    "context": ""
                }
            }

        try:
            # Enrichissement avec RAG (avec gestion d'erreur)
            rag_results = self.process_query(user_input, history_context=history)

            # Intégration du contexte RAG dans l'opération
            operation = {
                "operation": "chat",
                "parameters": {
                    "input": user_input,
                    "context": rag_results.get("enriched_context", "")
                }
            }

            return operation
        except Exception as e:
            self.logger.error(f"Erreur lors de la détection d'opération: {str(e)}")
            # Retour d'une opération par défaut en cas d'erreur
            return {
                "operation": "chat",
                "parameters": {
                    "input": user_input,
                    "context": ""
                }
            }
