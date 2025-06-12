import json
import logging
from typing import Dict, Any
from features.common.websocket_manager import send_progress
from features.cours_management.tools.test_tools import generate_exam
import asyncio

class TestAgent:
    def __init__(self):
        self.tool = generate_exam

    async def create_exam_async(self, course_data: Dict[str, Any], retries: int = 1) -> Dict[str, Any]:
        last_error = None

        for attempt in range(retries + 1):
            try:
                await send_progress("🧪 Generating final test...")

                raw = await self.tool.ainvoke({"course_data": course_data})
                exam = raw if isinstance(raw, dict) else json.loads(raw or "{}")

                if not exam:
                    raise ValueError("Empty response")

                exam.setdefault("course_id", course_data.get("course_id"))

                for field in ("course_id", "title", "description", "status", "content"):
                    if field not in exam:
                        raise KeyError(f"Missing field `{field}`")

                if isinstance(exam["content"], str):
                    exam["content"] = json.loads(exam["content"])

                await send_progress("✅ Test created!")
                return exam

            except Exception as e:
                last_error = e
                await send_progress(f"❌ Failed to create test (attempt {attempt + 1})")
                logging.warning(f"create_exam attempt {attempt + 1} failed: {e}")

        return {"error": "Format d'examen invalide", "details": str(last_error)}
