from __future__ import annotations

import operator
from typing import List, Optional, TypedDict, Annotated

from langchain_core.messages import BaseMessage

class GraphState(TypedDict, total=False):
    """Shared state for the course chatbot graph."""

    messages: Annotated[List[BaseMessage], operator.add]
    operation: Optional[str]
    result: Optional[dict]
    user_id: Optional[str]
    user_role: Optional[str]
    conversation_id: str
    pdf_bytes: Optional[bytes]
    rag_context: Optional[str]
    history: Optional[List[str]]
