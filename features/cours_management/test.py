if state["results"]:
    ai_txt = "\n".join(str(r.get("response", "")) for r in state["results"])
    conversation_memory.save_conversation(
        user_id=user_id,
        user_message="",
        assistant_message=ai_txt,
        conversation_id=conv_id,
        meta={"stage": "assistant_msg"}
    )