# example.py
import sys
import os
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
llm_client = OpenAILLMClient(model="gpt-4.1")  # Replace with your key
parser = RuleParser(llm_client, category=RuleCategory.ENTRY)

# -----------------------------
# User input rule
# -----------------------------
user_rule = "Prevent entries if my buying power is below $50,000 or my cash is less than $10,000."

# Parse user input into a RuleBlock
rule_block = parser.parse(user_rule)

# -----------------------------
# Market context
# -----------------------------
market_context = {
    "rsi": ohlcv['rsi'].iloc[-1],
    "current_time": 10 * 3600  # 10:00 AM in seconds
}

# -----------------------------
# Context hydration
# -----------------------------
# Collect all primitives from the rule block
primitives = [ext.primitive for ext in rule_block.extensions.values()]
global_account_fields = [
    "trading_blocked",
    "trade_suspended_by_user",
    "pattern_day_trader",
    "daytrade_count",
    "buying_power",
    "cash"
]

context_builder = ContextBuilder(alpaca_provider, global_account_fields=global_account_fields)
extensions = list(rule_block.extensions.values())
full_context = context_builder.hydrate(base_context=market_context, extensions=extensions)


print("Hydrated context with market + account data:")
print(full_context["account"])

# -----------------------------
# Rule evaluation
# -----------------------------
print("RSI value:", market_context["rsi"])

can_enter = rule_block.evaluate(full_context)
print("Can enter trade:", can_enter)
