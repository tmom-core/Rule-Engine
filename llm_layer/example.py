# example.py
import sys
import os
import pprint
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import ContextBuilder, Primitive, PrimitiveRegistry
from primitives import (
    comparison_evaluator,
    set_membership_evaluator,
    rate_limit_evaluator,
    accumulation_evaluator,
    sequence_evaluator,
    temporal_gate_evaluator,
    account_comparison_evaluator
)
from account_providers import AlpacaAccountProvider
from rule_parser import RuleParser
from engine import RuleCategory
from llm_layer.llm_client import LLMClient  # your implementation
from llm_layer.openai_client import OpenAILLMClient
import pandas as pd
import numpy as np
import talib
from dotenv import load_dotenv

load_dotenv("../.env")
import asyncio
import json
from llm_layer.data_ingestion import WebSocketIngestion

# -----------------------------
# Market data & Primitives
# -----------------------------
# (Primitives and Provider setup remains the same, but we don't need the MockMarketDataProvider anymore)

# -----------------------------
# Register primitives
# -----------------------------
# Market-data only
# Note: 'rsi' might not be available in the raw stream unless calculated or provided. 
# For this example, we'll assume the rule checks 'price' which is available.
PrimitiveRegistry.register(
    Primitive("comparison", comparison_evaluator, required_context=["rsi"])
)
PrimitiveRegistry.register(
    Primitive("temporal_gate", temporal_gate_evaluator, required_context=["current_time"])
)

# Account-data primitives — no hardcoded fields
PrimitiveRegistry.register(
    Primitive("set_membership", set_membership_evaluator)
)
PrimitiveRegistry.register(
    Primitive("rate_limit", rate_limit_evaluator)
)
PrimitiveRegistry.register(
    Primitive("accumulation", accumulation_evaluator)
)
PrimitiveRegistry.register(
    Primitive("sequence", sequence_evaluator)
)
PrimitiveRegistry.register(
    Primitive("account_comparison", account_comparison_evaluator)
)

# -----------------------------
# Alpaca account provider
# -----------------------------
alpaca_provider = AlpacaAccountProvider(
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("SECRET_KEY"),
    paper=True
)

# -----------------------------
# Initialize LLM client + parser
# -----------------------------
llm_client = OpenAILLMClient(model="gpt-4.1")
parser = RuleParser(llm_client, category=RuleCategory.ENTRY)

class MockUserActionProvider:
    def get_history(self, metrics: list) -> dict:
        history = {}
        for metric in metrics:
            history[metric] = [] # Return empty for now
        return history

user_action_provider = MockUserActionProvider()
global_account_fields = [
    "trading_blocked",
    "trade_suspended_by_user",
    "pattern_day_trader",
    "daytrade_count",
    "buying_power",
    "cash"
]

# -----------------------------
# Main Async Execution
# -----------------------------
async def main():
    # User input rule
    user_rule = "Don't buy BTC if the price is above 85,000"
    print(f"USER RULE: '{user_rule}'")
    
    print("\n[STEP 1] LLM Parsing & Context Skeleton Creation")
    rule_block, context_skeleton = parser.parse(user_rule)
    print(f"  -> Generated Skeleton (Needs: {context_skeleton.market_data})")

    # Context Builder
    context_builder = ContextBuilder(
        account_provider=alpaca_provider, 
        user_action_provider=user_action_provider,
        global_account_fields=global_account_fields
    )

    evaluation_results = []
    
    # Websocket setup
    ws_url = "wss://tmom-app-backend.onrender.com/ws/market-state"
    client = WebSocketIngestion(ws_url)

    print(f"\n[STEP 2] connecting to {ws_url} for 30 seconds...")

    async def on_message(msg):
        try:
            data = json.loads(msg)
            # Data format expected: {"event_type": "market_state", "symbol": "BTC", "current_time": "...", "price": ...}
            
            # 1. Build Market Context
            market_context = {}
            # Map known fields
            if "price" in data:
                market_context["price"] = data["price"]
            if "current_time" in data:
                market_context["current_time"] = data["current_time"]
            if "symbol" in data:
                market_context["symbol"] = data["symbol"]
                
            
            # 2. Hydrate Full Context
            # We assume account data is relatively static or fetched efficiently
            full_context = context_builder.hydrate(base_context=market_context, context_skeleton=context_skeleton)
            
            # 3. Evaluate Rule
            can_enter = rule_block.evaluate(full_context)
            
            # 4. Record Result
            packet = {
                "timestamp": full_context.get("current_time"),
                "price": full_context.get("price"),
                "result": can_enter
            }
            evaluation_results.append(packet)
            # Optional: print dot or small status to show aliveness
            print(".", end="", flush=True)

        except Exception as e:
            print(f"Error processing message: {e}")

    try:
        await asyncio.wait_for(client.listen(on_message), timeout=30)
    except asyncio.TimeoutError:
        print("\n\nFinished listening (30s timeout).")
    except Exception as e:
        print(f"\nError during listening: {e}")

    print("\n[STEP 3] Evaluation Results Summary")
    print("-" * 60)
    print(f"{'TIMESTAMP':<30} | {'PRICE':<10} | {'RESULT'}")
    print("-" * 60)
    for res in evaluation_results:
        print(f"{res['timestamp']:<30} | {res['price']:<10} | {res['result']}")
    print("-" * 60)
    print(f"Total evaluations: {len(evaluation_results)}")

if __name__ == "__main__":
    asyncio.run(main())
