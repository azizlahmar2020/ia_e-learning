from langchain_core.tools import tool
from langchain_groq import ChatGroq
from features.cours_management.prompts.Test_prompt import build_test_prompt
import os

@tool
def generate_exam(course_data: dict) -> dict:
    """
    Génère un test structuré grâce à LangChain/Groq.
    """
    prompt, parser = build_test_prompt()
    llm = ChatGroq(
        model_name="llama3-8b-8192",
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.2
    )
    chain = prompt | llm | parser
    return chain.invoke({"course_data": course_data})
