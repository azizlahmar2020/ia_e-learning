# IA E-learning

This project contains various agents and workflows using LangGraph and LangChain.

## Tool calling workflow

A new example workflow is available at `features/chatbot/workflow/function_graph.py`.
It demonstrates how to build a LangGraph that relies on the Groq Llama model's
function-calling ability to interact with tools while persisting memory using
`SqliteSaver`.

### Quick example

```python
from langchain_core.messages import HumanMessage
from features.chatbot.workflow.function_graph import workflow

state = {
    "messages": [HumanMessage(content="Quelle est la date aujourd'hui ?")],
    "results": [],
    "error": None,
}

response = workflow.invoke(state)
print(response["results"])
```

This graph registers tools from `ChatbotTools`, `CourseTools` and
`UserTools`. The agent chooses which tool to call using Groq's function
calling capability and stores conversation history in
`tool_call_memory.db`.

It also exposes `answer_about_course`, a RAG powered tool that retrieves
course information from a Qdrant vector store before crafting the reply.
