from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema


def build_operation_prompt():
    system_message = (
        "Tu es l'assistant API de la plateforme e-learning. "
        "Analyse la requête et renvoie uniquement un JSON valides décrivant"
        " l'opération à effectuer. Les opérations possibles sont:"
        " get_users, get_user_by_id, create_user, update_user et delete_user."
        " Le JSON doit contenir les clés 'operation' et 'parameters'."
    )

    response_schemas = [
        ResponseSchema(name="operation", description="Opération API détectée"),
        ResponseSchema(name="parameters", description="Paramètres associés"),
    ]

    parser = StructuredOutputParser.from_response_schemas(response_schemas)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_message),
            ("human", "Requête : {input}"),
            ("human", "Réponds uniquement avec le JSON final."),
        ]
    )
    return prompt, parser
