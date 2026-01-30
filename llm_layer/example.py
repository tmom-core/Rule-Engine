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
# -----------------------------
# Market data
# -----------------------------
np.random.seed(42)
minutes = pd.date_range("2026-01-06 09:30", periods=15, freq="T")
price = 100 + np.cumsum(np.random.randn(15))

ohlcv = pd.DataFrame({
    "timestamp": minutes,
    "open": price + np.random.randn(15),
    "high": price + np.random.rand(15),
    "low": price - np.random.rand(15),
    "close": price,
    "volume": np.random.randint(100, 500, size=15)
})

# Add RSI column using TA-Lib
ohlcv['rsi'] = talib.RSI(ohlcv['close'], timeperiod=10)

# -----------------------------
# Register primitives
# -----------------------------
# Market-data only
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
    api_key=os.getenv("API_KEY"),  # pick up from .env
    api_secret=os.getenv("SECRET_KEY"),
    paper=True
)



# -----------------------------
# Initialize LLM client + parser
# -----------------------------
llm_client = OpenAILLMClient(model="gpt-4.1")
parser = RuleParser(llm_client, category=RuleCategory.ENTRY)

# -----------------------------
# User input rule
# -----------------------------
user_rule = "Buy BTC if the price is below 85,000"

# Parse user input
print(f"USER RULE: '{user_rule}'")
print("\n[STEP 1] LLM Parsing & Context Skeleton Creation")
rule_block, context_skeleton = parser.parse(user_rule)

print(f"  -> Generated Skeleton:")
print(f"     Context Skeleton: {context_skeleton.model_dump_json(indent=2)}")
print(f"     Market Data:    {context_skeleton.market_data}")
print(f"     Account Fields: {context_skeleton.account_fields}")

# -----------------------------
# Mock Data Providers
# -----------------------------
class MockMarketDataProvider:
    def __init__(self, data_source: pd.DataFrame):
        self.data = data_source

    def fetch_data(self, required_metrics: list) -> dict:
        """
        Fetch only the metrics requested by the Context Skeleton.
        """
        snapshot = {}
        latest_row = self.data.iloc[-1]
        
        for metric in required_metrics:
            if metric in latest_row:
                snapshot[metric] = latest_row[metric]
            elif metric == "price": # Common alias
                snapshot["price"] = latest_row["close"]
            else:
                print(f"WARNING: Market data metric '{metric}' not found.")
                snapshot[metric] = 0 # Default safety
        
        # Always add time
        snapshot["current_time"] = "2026-01-30T14:32:18.123Z"
        return snapshot

# Initialize Market Provider
market_provider = MockMarketDataProvider(ohlcv)

class MockUserActionProvider:
    def get_history(self, metrics: list) -> dict:
        """
        Returns timestamped history for requested metrics.
        """
        history = {}
        # current_time is "2026-01-30T14:32:18.123Z" (approx 14:32)
        # 14:32 = 14*3600 + 32*60 + 18 = 52338
        
        # We need past ISO times for trades.
        # Let's say trades happened at 14:00, 14:15, 14:25
        
        for metric in metrics:
            if metric == "trades":
                history["trades"] = [
                    "2026-01-30T14:00:00.000Z",
                    "2026-01-30T14:15:00.000Z",
                    "2026-01-30T14:25:00.000Z"
                ]
            else:
                history[metric] = []
        return history

user_action_provider = MockUserActionProvider()

# -----------------------------
# Context hydration
# -----------------------------
print("\n[STEP 2] Context Hydration (Filling the Skeleton)")
# 1. Get Market Data
market_metrics = context_skeleton.market_data
market_context = market_provider.fetch_data(market_metrics)
print(f"  -> Fetched Market Data: {market_context}")

# 2. Get Account Data
# Define globals (usually config)
global_account_fields = [
    "trading_blocked",
    "trade_suspended_by_user",
    "pattern_day_trader",
    "daytrade_count",
    "buying_power",
    "cash"
]

context_builder = ContextBuilder(
    account_provider=alpaca_provider, 
    user_action_provider=user_action_provider,
    global_account_fields=global_account_fields
)
full_context = context_builder.hydrate(base_context=market_context, context_skeleton=context_skeleton)

print(f"  -> Fetched Account Data: {full_context.get('account', {})}")
print(f"  -> Final Populated Context:")
pprint.pprint(full_context)


# -----------------------------
# Rule evaluation
# -----------------------------
print("\n[STEP 3] Rule Evaluation")
can_enter = rule_block.evaluate(full_context)
print(f"  -> RuleBlock Evaluation Result: {can_enter}")

# Final Result Packet
result_packet = {
    "rule": user_rule,
    "result": can_enter,
    "timestamp": full_context.get("current_time"),
    "symbol": full_context.get("symbol")
}

print("\n-----------------------------")
print("FINAL OUTPUT:")
pprint.pprint(result_packet)
print("-----------------------------")
