# prompts.py
import json

# Full Alpaca account fields available for rules
ACCOUNT_FIELDS = [
    "account_blocked",
    "account_number",
    "accrued_fees",
    "buying_power",
    "cash",
    "created_at",
    "crypto_status",
    "currency",
    "daytrade_count",
    "daytrading_buying_power",
    "equity",
    "id",
    "initial_margin",
    "last_equity",
    "last_maintenance_margin",
    "long_market_value",
    "maintenance_margin",
    "multiplier",
    "non_marginable_buying_power",
    "options_approved_level",
    "options_buying_power",
    "options_trading_level",
    "pattern_day_trader",
    "pending_transfer_in",
    "pending_transfer_out",
    "portfolio_value",
    "regt_buying_power",
    "short_market_value",
    "shorting_enabled",
    "sma",
    "status",
    "trade_suspended_by_user",
    "trading_blocked",
    "transfers_blocked"
]

from primitives_manifest import PRIMITIVE_MANIFEST

def build_system_prompt() -> str:
    """
    Builds the system prompt for the LLM to parse trading rules.
    Includes a list of all valid primitives and account fields.
    """
    return f"""
You are a rule parser for a deterministic trading rule engine.

Rules:
- Output ONLY valid JSON
- Follow the schema exactly
- Use ONLY the provided primitives
- If information is missing, return status = "needs_clarification"
- If unsupported, return status = "unsupported"
- Return the following keys:
  - "status": "ok" | "needs_clarification" | "unsupported"
  - "reason": optional explanation
  - "rule": object with "extensions" and "conditions"
- Convert times to seconds since midnight (e.g., 9:30 AM → 34200)
- Convert numeric thresholds to numbers
- Use unique IDs for each extension
- Return ONLY JSON, nothing else

Available primitives:
{json.dumps(PRIMITIVE_MANIFEST, indent=2)}

Available account fields (choose ONLY from these for account-related primitives):
{json.dumps(ACCOUNT_FIELDS, indent=2)}

Example output:

{{
  "status": "ok",
  "rule": {{
    "extensions": [
      {{
        "id": "rsi_ok",
        "primitive": "comparison",
        "params": {{"left": "rsi", "op": ">", "right": 30}}
      }},
      {{
        "id": "time_ok",
        "primitive": "temporal_gate",
        "params": {{"start_time": 34200, "end_time": 41400}}
      }},
      {{
        "id": "bp_ok",
        "primitive": "account_comparison",
        "params": {{"field": "buying_power", "op": ">=", "value": 50000}}
      }}
    ],
    "conditions": {{"all": ["rsi_ok", "time_ok", "bp_ok"]}}
  }}
}}
"""
