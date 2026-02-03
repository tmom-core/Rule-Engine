# llm_layer/live_engine.py
import sys
import os
import pprint
import asyncio
import json
import pandas as pd
from typing import Dict, Any, Set
from aiohttp import web, WSMsgType

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import ContextBuilder, Primitive, PrimitiveRegistry, RuleBlock, RuleCategory
from primitives import (
    comparison_evaluator,
    temporal_gate_evaluator,
    account_comparison_evaluator
)
from account_providers import AlpacaAccountProvider
from rule_parser import RuleParser
from llm_layer.openai_client import OpenAILLMClient
from llm_layer.data_ingestion import WebSocketClient
from dotenv import load_dotenv

load_dotenv("../.env")

# -----------------------------
# Configuration & Registries
# -----------------------------

# Register Primitives (subset needed for the example)
if "comparison" not in PrimitiveRegistry._registry:
    PrimitiveRegistry.register(
        Primitive("comparison", comparison_evaluator, required_context=["price"])
    )
if "temporal_gate" not in PrimitiveRegistry._registry:
    PrimitiveRegistry.register(
        Primitive("temporal_gate", temporal_gate_evaluator, required_context=["current_time"])
    )
if "account_comparison" not in PrimitiveRegistry._registry:
    PrimitiveRegistry.register(
        Primitive("account_comparison", account_comparison_evaluator)
    )

# -----------------------------
# Shared State
# -----------------------------
class EngineState:
    def __init__(self):
        self.user_has_acted = False
        self.lock = asyncio.Lock()

    async def set_user_action(self, acted: bool):
        async with self.lock:
            self.user_has_acted = acted
    
    async def get_and_reset_user_action(self) -> bool:
        async with self.lock:
            acted = self.user_has_acted
            self.user_has_acted = False  # Reset after reading
            return acted

state = EngineState()

# Global set of connected clients for result broadcasting
connected_clients: Set[web.WebSocketResponse] = set()

# -----------------------------
# WebSocket Handlers
# -----------------------------

async def user_activity_handler(msg: str):
    """
    Listens for user activity on the websocket.
    Any message received here counts as a 'user action' for the current interval.
    """
    try:
        data = json.loads(msg)
        # In a real scenario, we might check data['alpaca_event_type'] == 'fill' or similar.
        # For now, per instructions: "when a user action does come true"
        # We assume availability of this message implies an action occurred.
        print(f" [USER ACTION RECEIVED] {data.get('activity_id', 'unknown_id')}")
        await state.set_user_action(True)
    except json.JSONDecodeError:
        print(f" [USER ACTION ERROR] Invalid JSON: {msg[:50]}...")
    except Exception as e:
        print(f" [USER ACTION ERROR] {e}")

async def run_market_engine(
    ws_url: str,
    # result_ws_url removed as we now broadcast
    rule_block: RuleBlock,
    context_builder: ContextBuilder,
    context_skeleton: Any
):
    client = WebSocketClient(ws_url)
    
    print(f" [MARKET] Connecting to {ws_url}...")
    # No longer connecting to result_ws_url explicitly
    
    async def market_handler(msg: str):
        try:
            data = json.loads(msg)
            
            # 1. Build Base Context from Market Data
            market_context = {}
            if "price" in data:
                market_context["price"] = data["price"]
            if "current_time" in data:
                market_context["current_time"] = data["current_time"]
            if "symbol" in data:
                market_context["symbol"] = data["symbol"]

            # 2. Hydrate Full Context (fetches account data if needed)
            full_context = context_builder.hydrate(
                base_context=market_context, 
                context_skeleton=context_skeleton
            )

            # 3. Evaluate Rule
            # rule_result is True (Signal Triggered) or False (No Signal)
            rule_result = rule_block.evaluate(full_context)

            # 4. Get and Reset User Action State
            # This captures if the user acted since the last evaluation
            user_action_bool = await state.get_and_reset_user_action()

            # 5. Calculate Deviation
            # True if they disagree (Rule says True vs User False, or Rule False vs User True)
            # False if they agree
            deviation = rule_result != user_action_bool

            # 6. Output Result
            output_payload = {
                "timestamp": market_context.get("current_time"),
                "price": market_context.get("price"),
                "rule": rule_result,
                "action": user_action_bool,
                "deviation": deviation
            }
            
            # Print to console
            print(
                f"TIME: {output_payload['timestamp']} | "
                f"PRICE: {output_payload['price']:<8} | "
                f"RULE: {str(rule_result):<5} | "
                f"ACTION: {str(user_action_bool):<5} | "
                f"DEVIATION: {str(deviation)}"
            )
            
            # Broadcast to all connected WebSocket clients
            if connected_clients:
                # Iterate over a copy to avoid modification issues during iteration
                for ws in list(connected_clients):
                    try:
                        await ws.send_json(output_payload)
                    except Exception as send_err:
                        print(f" [RESULT STREAM ERROR] {send_err}")
                        # Clean up dead connections lazily or rely on the handler's finally block
                        
        except Exception as e:
            print(f" [MARKET ENGINE ERROR] {e}")

    await client.listen(market_handler)


# -----------------------------
# Main Setup
# -----------------------------
async def handle_health(request):
    return web.Response(text="OK")

async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    print(" [WEBSOCKET] Client connected")
    connected_clients.add(ws)
    
    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                # Optional: Handle incoming messages from clients if needed
                pass
            elif msg.type == WSMsgType.ERROR:
                print(f" [WEBSOCKET] Connection closed with exception {ws.exception()}")
    finally:
        connected_clients.remove(ws)
        print(" [WEBSOCKET] Client disconnected")
    
    return ws

async def start_web_server():
    app = web.Application()
    app.add_routes([
        web.get('/', handle_health),
        web.get('/health', handle_health),
        web.get('/ws/engine-output', websocket_handler)
    ])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f" [SERVER] Listening on port {port}")
    return runner

async def main():
    # 1. Hardware/Provider Setup
    alpaca_provider = AlpacaAccountProvider(
        api_key=os.getenv("API_KEY"),
        api_secret=os.getenv("SECRET_KEY"),
        paper=True
    )
    
    context_builder = ContextBuilder(
        account_provider=alpaca_provider,
        user_action_provider=None
    )

    # 2. Define Rule (Hardcoded or Parsed)
    # Using a simple hardcoded rule for "Price > X" to test easily
    # Or valid LLM parsing if configured. Let's use the parser for realism.
    llm_client = OpenAILLMClient(model="gpt-4.1")
    parser = RuleParser(llm_client, category=RuleCategory.ENTRY)
    
    user_rule_text = "Enter trade if price is above 50000"
    print(f"Initializing Engine with Rule: '{user_rule_text}'")
    
    try:
        rule_block, context_skeleton = parser.parse(user_rule_text)
    except Exception as e:
        print(f"Failed to parse rule: {e}")
        return

    # 3. Start Websockets
    user_ws_url = "wss://tmom-app-backend.onrender.com/ws/user-activity"
    market_ws_url = "wss://tmom-app-backend.onrender.com/ws/market-state"
    # Result URL is now hosted locally

    user_ws = WebSocketClient(user_ws_url)

    # Create tasks
    print("Starting listeners...")
    
    # Start Web Server (Health + WebSocket)
    web_runner = await start_web_server()
    
    task_user = asyncio.create_task(user_ws.listen(user_activity_handler))
    task_market = asyncio.create_task(run_market_engine(
        market_ws_url, 
        rule_block, 
        context_builder, 
        context_skeleton
    ))

    # Keep alive
    try:
        await asyncio.gather(task_user, task_market)
    finally:
        await web_runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nEngine stopped.")
