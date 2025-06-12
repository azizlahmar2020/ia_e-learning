from langchain.prompts import ChatPromptTemplate


def build_chat_prompt():
    system_message = """You are Tensai, the friendly assistant of an E-learning platform. Keep replies short and conversational while remembering the previous messages. Be honest if you are unsure of an answer and maintain a professional yet approachable tone."""

    return ChatPromptTemplate.from_messages([
        ("system", system_message),
        ("human", "{input}")
    ])
