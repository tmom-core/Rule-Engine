from engine import RuleBlock, RuleCategory, Primitive, PrimitiveRegistry, ContextBuilder
from primitives import comparison_evaluator, temporal_gate_evaluator, account_comparison_evaluator
from account_providers import AlpacaAccountProvider
import pandas as pd
import numpy as np
import talib

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
PrimitiveRegistry.register(
    Primitive("comparison", comparison_evaluator, required_context=["rsi"])
)
PrimitiveRegistry.register(
    Primitive("temporal_gate", temporal_gate_evaluator, required_context=["current_time"])
)
PrimitiveRegistry.register(
    Primitive("account_comparison", account_comparison_evaluator, required_account_fields=["buying_power", "cash"])
)

# -----------------------------
# Define Rule Skeleton
# -----------------------------
rule_skeleton = {
    "extensions": [
        {"id": "rsi_ok", "primitive": "comparison", "params": {"left": "rsi", "op": ">", "right": 30}},
        {"id": "time_ok", "primitive": "temporal_gate", "params": {"start_time": 9.5 * 3600, "end_time": 11.5 * 3600}},
        {"id": "bp_ok", "primitive": "account_comparison", "params": {"field": "buying_power", "op": ">=", "value": 50000}},
        {"id": "cash_ok", "primitive": "account_comparison", "params": {"field": "cash", "op": ">=", "value": 100000}}
    ],
    "conditions": {"all": ["rsi_ok", "time_ok", "bp_ok", "cash_ok"]}
}

rule_block = RuleBlock(category=RuleCategory.ENTRY, skeleton=rule_skeleton)

# -----------------------------
# Market context
# -----------------------------
market_context = {
    "rsi": ohlcv['rsi'].iloc[-1],
    "current_time": 10 * 3600  # 10:00 AM in seconds
}

# -----------------------------
# Alpaca account provider
# -----------------------------
alpaca_provider = AlpacaAccountProvider(
    api_key=None,  # will pick up from .env
    api_secret=None,
    paper=True
)

# -----------------------------
# Context hydration
# -----------------------------
# Collect all primitives for required account fields
primitives = [ext.primitive for ext in rule_block.extensions.values()]
global_account_fields = ["pattern_day_trader", "daytrade_count", "trading_blocked", "trade_suspended_by_user"]

context_builder = ContextBuilder(alpaca_provider, global_account_fields=global_account_fields)
full_context = context_builder.hydrate(base_context=market_context, primitives=primitives)

print("Hydrated context with market + account data:")
print(full_context["account"])

# -----------------------------
# Rule evaluation (pre-flight validation integrated)
# -----------------------------
print("full_context:", full_context)
can_enter = rule_block.evaluate(full_context)
print("Can enter trade:", can_enter)
