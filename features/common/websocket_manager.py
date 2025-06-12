from fastapi import WebSocket, WebSocketDisconnect

clients = {}

async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    user_id=1
    clients[user_id] = websocket
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        clients.pop(user_id, None)

async def send_progress( message: str):
    user_id=1

    print(f"[WS] {user_id} ← {message}")  # ✅ Affiche dans la console

    websocket = clients.get(user_id)
    if websocket:
        try:
            await websocket.send_text(message)
        except:
            clients.pop(user_id, None)
