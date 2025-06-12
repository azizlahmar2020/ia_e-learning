from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema

def build_operation_prompt():
    system_message = """Vous êtes un assistant spécialisé en API REST pour une plateforme e-learning.
    Vous devez analyser une requête utilisateur et renvoyer STRICTEMENT un JSON bien formé.

    **📌 Endpoints disponibles**
    - 🔍 Obtenir la liste complète des utilisateurs : `get_users`
    - 🔎 Obtenir un utilisateur spécifique par ID : `get_user_by_id`
    - 🆕 Créer un nouveau utilisateur : `create_user`
    - ✏️ Modifier un utilisateur : `update_user`
    - ❌ Supprimer un utilisateur : `delete_user`
    
    **Règles obligatoires de sortie JSON**:
        1. Toujours retourner un seul objet JSON
        2. Les clés de l’objet principal doivent être:
            - "operation": [valeur = "get_users", "get_user_by_id", "create_user", "update_user", "delete_user"]
            - "parameters": {{ … }} (données structurées spécifiques à chaque opération)
        
        3. Aucune autre information en dehors de cet objet JSON.
        
        **Exemple**: {{ "operation": "get_users", "parameters": {{ "users": [ {{ "user_id": 1, "firstname": "Alice", "lastname": "Young", "email": "aliceyoung@example.com", "phone": "25874963", "user_role": "Student" }}, {{ "user_id": 2, "firstname": "Bob", "lastname": "Smith", "email": "bobsmith@example.com", "phone": "25874964", "user_role": "Professor" }} ] }} }}

    """

    response_schemas = [
        ResponseSchema(name="operation", description="Opération API détectée"),
        ResponseSchema(name="parameters", description="Données structurées du utilisateur")
    ]

    parser = StructuredOutputParser.from_response_schemas(response_schemas)

    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", "Requête : {input}"),
        ("human", "Génère UNIQUEMENT le JSON avec du contenu COMPLET et FINAL :"),
    ]), parser