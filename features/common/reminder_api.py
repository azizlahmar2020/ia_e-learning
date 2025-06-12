from fastapi import APIRouter, WebSocket, WebSocketDisconnect, BackgroundTasks
from datetime import datetime, timezone
import asyncio
import httpx

router = APIRouter()
clients = {}  # user_id → WebSocket

ORACLE_REMINDER_API = "https://apex.oracle.com/pls/apex/naxxum/reminders/"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0"
}

# ─────────── WebSocket: Connexion client ───────────
@router.websocket("/ws/reminder/{user_id}")
async def reminder_ws(websocket: WebSocket, user_id: int):
    await websocket.accept()
    clients[user_id] = websocket
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        clients.pop(user_id, None)

# ─────────── Rappel planifié et persisté ───────────
@router.post("/reminders/")
async def create_reminder(data: dict, background_tasks: BackgroundTasks):
    user_id = data["user_id"]
    session_id = data["session_id"]
    reminder_time = datetime.fromisoformat(data["reminder_time"])

    # Assure status is present
    if "status" not in data:
        data["status"] = "active"

    if reminder_time.tzinfo is None:
        reminder_time = reminder_time.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    delay = (reminder_time - now).total_seconds()

    # Sauvegarder dans Oracle APEX
    async with httpx.AsyncClient() as client:
        await client.post(ORACLE_REMINDER_API, json=data, headers=HEADERS)

    if delay > 0:
        background_tasks.add_task(schedule_reminder, user_id, session_id, delay)
    else:
        background_tasks.add_task(send_reminder, user_id, f"⚠️ Session {session_id} is starting now!")

    return {"status": "Reminder scheduled", "user_id": user_id, "session_id": session_id}

# ─────────── Tâche planifiée asynchrone ───────────
async def schedule_reminder(user_id: int, session_id: int, delay: float):
    await asyncio.sleep(delay)
    await send_reminder(user_id, f"⏰ Your session {session_id} is about to start!")

# ─────────── Notification temps réel + fallback ───────────
async def send_reminder(user_id: int, message: str):
    ws = clients.get(user_id)
    if ws:
        print(f"[📢] Sending reminder to user {user_id}: {message}")
        await ws.send_json({"type": "reminder", "message": message})
    else:
        print(f"[❌] WebSocket inactive. Logging reminder for user {user_id}")
        # Fallback: log as missed in Oracle APEX
        async with httpx.AsyncClient() as client:
            await client.post(ORACLE_REMINDER_API, json={
                "user_id": user_id,
                "session_id": 0,
                "reminder_time": datetime.now(timezone.utc).isoformat(),
                "status": "missed"
            }, headers=HEADERS)
