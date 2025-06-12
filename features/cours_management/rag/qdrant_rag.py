import logging
from typing import List, Dict, Any, Optional, Tuple
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse


class QdrantRAG:
    def __init__(self, collection_name="course_knowledge", host="localhost", port=6333):
        # Configuration du logger
        self.logger = logging.getLogger(__name__)

        # Initialisation des attributs
        self.collection_name = collection_name
        self.client = None
        self.vectorstore = None
        self.is_available = False
        self.embeddings = None

        # Modèle d'embedding
        try:
            self.embeddings = FastEmbedEmbeddings(model_name="BAAI/bge-small-en-v1.5")
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation du modèle d'embedding: {str(e)}")

        # Text splitter pour découper les documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )

        # Tentative d'initialisation du client Qdrant avec gestion d'erreur
        try:
            self.client = QdrantClient(host, port=port)
            # Vérification de la connexion
            self._create_collection_if_not_exists()

            # Initialisation du vectorstore si le client est disponible
            if self.client and self.embeddings:
                self.vectorstore = QdrantVectorStore(
                    client=self.client,
                    collection_name=self.collection_name,
                    embedding=self.embeddings,  # <-- CORRECTION ICI
                )
                self.is_available = True
                self.logger.info(f"Connexion à Qdrant établie avec succès sur {host}:{port}")
        except (ResponseHandlingException, UnexpectedResponse, ConnectionError) as e:
            self.logger.error(f"Erreur de connexion à Qdrant: {str(e)}")
            self.logger.warning("QdrantRAG fonctionnera en mode dégradé (sans persistance)")
        except Exception as e:
            self.logger.error(f"Erreur inattendue lors de l'initialisation de Qdrant: {str(e)}")
            self.logger.warning("QdrantRAG fonctionnera en mode dégradé (sans persistance)")

    def _create_collection_if_not_exists(self):
        """Crée la collection pour le RAG si elle n'existe pas"""
        if not self.client:
            return

        try:
            collections = self.client.get_collections().collections
            if not any(collection.name == self.collection_name for collection in collections):
                # Création d'une collection pour les embeddings
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=384,  # Taille des vecteurs pour bge-small-en-v1.5
                        distance=models.Distance.COSINE
                    )
                )
                self.logger.info(f"Collection '{self.collection_name}' créée avec succès")
        except Exception as e:
            self.is_available = False
            self.logger.error(f"Erreur lors de la création de la collection: {str(e)}")
            # Ne pas propager l'exception pour permettre un fonctionnement dégradé
            # mais marquer comme non disponible

    def add_texts(self, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Ajoute des textes à la base de connaissances"""
        if not self.is_available or not self.vectorstore:
            self.logger.warning("Impossible d'ajouter des textes: Qdrant n'est pas disponible")
            return False

        try:
            # Vérification des entrées
            if not texts:
                self.logger.warning("Aucun texte à ajouter")
                return False

            if metadatas and len(texts) != len(metadatas):
                self.logger.warning("Le nombre de textes et de métadonnées ne correspond pas")
                return False

            # Découpage des textes en chunks
            if metadatas:
                documents = [Document(page_content=text, metadata=metadata)
                             for text, metadata in zip(texts, metadatas)]
            else:
                documents = [Document(page_content=text) for text in texts]

            chunks = self.text_splitter.split_documents(documents)

            if not chunks:
                self.logger.warning("Aucun chunk généré après découpage des textes")
                return False

            # Ajout au vectorstore
            self.vectorstore.add_documents(chunks)
            self.logger.info(f"{len(chunks)} chunks ajoutés avec succès à la collection {self.collection_name}")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'ajout de textes: {str(e)}")
            return False

    def add_course_content(self, course_id: str, title: str, content: str,
                           metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Ajoute le contenu complet d'un cours à la base de connaissances"""
        if not self.is_available or not self.vectorstore:
            self.logger.warning(f"Impossible d'indexer le cours {course_id}: Qdrant n'est pas disponible")
            return False

        try:
            # Préparer les documents à indexer
            docs = []
            metas = []

            # 1️⃣ Indexer le résumé du cours + liste des chapitres
            chapters = metadata.get("chapters", [])
            chapter_titles = "\n".join([f"- {ch.get('title','')}" for ch in chapters if ch.get('title')])
            summary = (
                f"Titre: {title}\n"
                f"Résumé: {metadata.get('description', '')}\n"
                f"Audience: {metadata.get('target_audience', '')}\n"
                f"Tags: {metadata.get('tags', '')}\n"
                f"Chapitres:\n{chapter_titles if chapter_titles else 'Aucun'}"
            )
            docs.append(summary)
            metas.append({**metadata, "course_id": str(course_id), "title": title, "type": "course_summary"})

            # 2️⃣ Indexer le contenu principal du cours (si présent)
            if content and content.strip():
                docs.append(content)
                metas.append({**metadata, "course_id": str(course_id), "title": title, "type": "course_content"})

            # 3️⃣ Indexer les chapitres (si présents)
            chapters = metadata.get("chapters", [])
            for ch in chapters:
                ch_title = ch.get("title") or ch.get("TITLE", "")
                ch_content = ch.get("content") or ch.get("CONTENT", "")
                if ch_content:
                    docs.append(f"Chapitre: {ch_title}\n{ch_content}")
                    metas.append({**metadata, "course_id": str(course_id), "title": ch_title, "type": "chapter"})

            # 4️⃣ Indexer les quiz (si présents)
            quizzes = metadata.get("quizzes", [])
            for quiz in quizzes:
                quiz_title = quiz.get("title", "")
                quiz_content = quiz.get("content", "")
                if isinstance(quiz_content, dict) or isinstance(quiz_content, list):
                    quiz_content = str(quiz_content)
                docs.append(f"Quiz: {quiz_title}\n{quiz_content}")
                metas.append({**metadata, "course_id": str(course_id), "title": quiz_title, "type": "quiz"})

            # 5️⃣ Indexer le test/examen (si présent)
            exam = metadata.get("exam", {})
            if exam:
                exam_title = exam.get("title", "")
                exam_content = exam.get("content", "")
                if isinstance(exam_content, dict) or isinstance(exam_content, list):
                    exam_content = str(exam_content)
                docs.append(f"Examen: {exam_title}\n{exam_content}")
                metas.append({**metadata, "course_id": str(course_id), "title": exam_title, "type": "exam"})

            self.logger.info(f"Indexation de {len(docs)} documents pour le cours {course_id}")
            # Ajout au vectorstore
            result = self.add_texts(docs, metas)
            if result:
                self.logger.info(f"Cours {course_id} indexé avec succès")
            else:
                self.logger.error(f"Echec de l'indexation du cours {course_id}")
            return result
        except Exception as e:
            self.logger.error(f"Erreur lors de l'indexation du cours {course_id}: {str(e)}")
            return False

    def search(self, query: str, k: int = 3) -> List[Document]:
        """Recherche des documents pertinents pour une requête"""
        if not self.is_available or not self.vectorstore:
            self.logger.warning("Impossible d'effectuer la recherche: Qdrant n'est pas disponible")
            return []

        if not query or not query.strip():
            self.logger.warning("Requête de recherche vide")
            return []

        try:
            k = max(1, min(k, 10))  # Limiter k entre 1 et 10
            results = self.vectorstore.similarity_search(query, k=k)
            self.logger.info(f"Recherche effectuée avec succès: {len(results)} résultats trouvés")
            return results
        except Exception as e:
            self.logger.error(f"Erreur lors de la recherche: {str(e)}")
            return []

    def search_with_score(self, query: str, k: int = 3) -> List[Tuple[Document, float]]:
        """Recherche des documents pertinents avec scores de similarité"""
        if not self.is_available or not self.vectorstore:
            self.logger.warning("Impossible d'effectuer la recherche avec score: Qdrant n'est pas disponible")
            return []

        if not query or not query.strip():
            self.logger.warning("Requête de recherche vide")
            return []

        try:
            k = max(1, min(k, 10))  # Limiter k entre 1 et 10
            results = self.vectorstore.similarity_search_with_score(query, k=k)
            self.logger.info(f"Recherche avec score effectuée avec succès: {len(results)} résultats trouvés")
            return results
        except Exception as e:
            self.logger.error(f"Erreur lors de la recherche avec score: {str(e)}")
            return []

    def delete_by_course_id(self, course_id: str) -> bool:
        """Supprime tous les documents liés à un cours spécifique"""
        if not self.is_available or not self.client:
            self.logger.warning(f"Impossible de supprimer le cours {course_id}: Qdrant n'est pas disponible")
            return False

        if not course_id:
            self.logger.warning("L'identifiant du cours est requis pour la suppression")
            return False

        try:
            # Conversion en string pour assurer la compatibilité
            course_id_str = str(course_id)

            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.course_id",
                            match=models.MatchValue(value=course_id_str)
                        )
                    ]
                )
            )
            self.logger.info(f"Cours {course_id} supprimé avec succès de l'index")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de la suppression du cours {course_id}: {str(e)}")
            return False

    def delete_by_parent_course_id(self, parent_course_id: str) -> bool:
        """Supprime tous les documents liés à un cours parent spécifique (chapitres)"""
        if not self.is_available or not self.client:
            self.logger.warning(
                f"Impossible de supprimer les chapitres du cours {parent_course_id}: Qdrant n'est pas disponible")
            return False

        if not parent_course_id:
            self.logger.warning("L'identifiant du cours parent est requis pour la suppression")
            return False

        try:
            # Conversion en string pour assurer la compatibilité
            parent_id_str = str(parent_course_id)

            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="metadata.parent_course_id",
                            match=models.MatchValue(value=parent_id_str)
                        )
                    ]
                )
            )
            self.logger.info(f"Chapitres du cours {parent_course_id} supprimés avec succès de l'index")
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de la suppression des chapitres du cours {parent_course_id}: {str(e)}")
            return False

    def add_texts(self, docs: list, metas: list) -> bool:
        try:
            if not self.vectorstore:
                self.logger.error("Vectorstore non initialisé")
                return False
            # docs: list[str], metas: list[dict]
            self.vectorstore.add_texts(texts=docs, metadatas=metas)
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'ajout de textes dans Qdrant: {str(e)}")
            return False
