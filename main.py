import os
import asyncio
from aiohttp import web, WSMsgType
from dotenv import load_dotenv

load_dotenv(".env")

# Import execution engine logic
from execution_engine import process_new_playbook, connected_clients

# -----------------------------
# Configuration & Registries
# -----------------------------



# -----------------------------
# Shared State
# Keep track of active background WebSocket tasks so we can cancel them
# if the frontend triggers a new rule.
active_trading_tasks = []

async def handle_health(request):
    """Simple health check endpoint."""
    return web.json_response({"status": "healthy", "service": "rule-engine-orchestrator"})

async def trigger_playbook(request):
    """
    GET /api/rules/trigger?user_id=123&playbook_id=abc
    Triggered by the frontend when a user saves a new rule to the database.
    """
    user_id = request.query.get("user_id")
    playbook_id = request.query.get("playbook_id")

    if not user_id or not playbook_id:
        return web.json_response({
            "error": "Missing 'user_id' or 'playbook_id' in query parameters."
        }, status=400)

    print(f" [API] Received Trigger for User: {user_id} | Playbook: {playbook_id}")

    # Cancel any existing market engine tasks so we don't have conflicting rules trading
    global active_trading_tasks
    if active_trading_tasks:
        print(f" [API] Cancelling {len(active_trading_tasks)} previously active engine tasks...")
        for task in active_trading_tasks:
            task.cancel()
        active_trading_tasks.clear()

    # Launch the new playbook execution flow in the background
    # This task fetches from DB -> parses -> patches DB -> pings frontend -> starts WS trading
    async def run_in_background():
        tasks = await process_new_playbook(user_id, playbook_id, connected_clients)
        if tasks:
            active_trading_tasks.extend(tasks)
            
    # Fire and forget
    asyncio.create_task(run_in_background())

    # Immediately respond to frontend so they aren't blocked waiting for LLM parsing
    return web.json_response({
        "status": "success",
        "message": "Engine triggered. Fetching and applying playbook in the background."
    })

async def websocket_handler(request):
    """
    WS /ws/engine-output
    Local Websocket endpoint so the frontend (or local GUI) can connect to this engine
    and watch the evaluation logs stream in real-time.
    """
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    print(" [WEBSOCKET] Engine Result Viewer Connected")
    connected_clients.add(ws)
    
    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                pass
            elif msg.type == WSMsgType.ERROR:
                print(f" [WEBSOCKET] Connection closed with exception {ws.exception()}")
    finally:
        connected_clients.remove(ws)
        print(" [WEBSOCKET] Engine Result Viewer Disconnected")
    
    return ws

def setup_routes(app: web.Application):
    app.router.add_get('/', handle_health)
    app.router.add_get('/health', handle_health)
    app.router.add_get('/api/rules/trigger', trigger_playbook)
    app.router.add_get('/ws/engine-output', websocket_handler)

async def start_web_server():
    """Initializes and runs the web server."""
    app = web.Application()
    setup_routes(app)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    
    print(f" [SERVER] Starting Orchestrator API on port {port}...")
    await site.start()
    
    # Keep the event loop running forever
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(start_web_server())
    except KeyboardInterrupt:
        print(" Engine Orchestrator stopped.")
        print("\nEngine stopped.")
