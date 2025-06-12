from langchain_groq import ChatGroq
from langchain_core.tools import tool
from features.cours_management.rag.qdrant_rag import QdrantRAG
import os
@tool
def answer_about_course(question: str, course_title: str = "") -> str:
    """
    Répond à toute question sur un cours (nombre de chapitres, résumé, quiz, test, etc.).
    """
    rag = QdrantRAG()
    # Ajoute des mots-clés pour aider la recherche
    query = f"{course_title}. {question}. chapitre, chapitres, titre, section"
    docs = rag.search(query, k=5)
    context = "\n\n".join([doc.page_content for doc in docs if doc.page_content])

    if not context:
        return "Je n'ai pas trouvé d'informations sur ce cours."

    llm = ChatGroq(
        model_name="llama3-8b-8192",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.4
    )
    prompt = f"""Tu es un assistant e-learning. Voici le contexte extrait du cours :
{context}

Question : {question}

Consignes :
- Si la question demande un résumé du cours, commence par une ou deux phrases qui expliquent l'objectif et le contenu global du cours, de façon claire et pédagogique.
- Ensuite, si pertinent, liste les chapitres avec leurs titres.
- Ne répète pas inutilement les titres ou les listes.
- Sois synthétique, professionnel et utile pour un élève.

.
"""
    response = llm.invoke(prompt)
    return response.content.strip()