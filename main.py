from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from features.cours_management.api import router as cours_router
from features.user_management.api import router as auth_router
from features.common.websocket_manager import websocket_endpoint
from features.cours_management.agents.schedule_agent import ScheduleAgent
from features.common.reminder_api import router as ws_router
from features.common.reminder_api import schedule_reminder

import requests
import asyncio
from datetime import datetime, timezone

# 🔄 Gestion du cycle de vie (startup/shutdown)
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🔁 [Startup] Loading reminders from Oracle APEX...")
    now = datetime.now(timezone.utc)

    try:

            url = f"https://apex.oracle.com/pls/apex/naxxum/elearning/reminderbyuser/1"
            resp = requests.get(url, headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0"
            }, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", data)

            for r in items:
                if r.get("status") == "active":
                    reminder_time = datetime.fromisoformat(r["reminder_time"])
                    delay = (reminder_time - now).total_seconds()
                    if delay > 0:
                        print(f"⏳ Scheduling reminder for user {r['user_id']} in {delay:.2f} seconds...")
                        asyncio.create_task(schedule_reminder(r["user_id"], r["session_id"], delay))
                    else:
                        print(f"⚠️ Missed reminder for user {r['user_id']} (past time)")
    except Exception as e:
        print(f"🔥 Error loading reminders: {str(e)}")

    yield
    print("👋 [Shutdown] Application stopped.")


# ────────────────────────── App ──────────────────────────
app = FastAPI(lifespan=lifespan)

app.include_router(ws_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

app.include_router(auth_router, prefix='/api')
app.include_router(cours_router)
app.websocket("/ws")(websocket_endpoint)

# ────────────────────── Launch ──────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
