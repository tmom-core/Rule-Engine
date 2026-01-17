# account_validation.py

from typing import Dict, List

# Define the global fields that must always be checked before evaluating a rule
GLOBAL_ACCOUNT_FIELDS = [
    "trading_blocked",
    "trade_suspended_by_user",
    "pattern_day_trader",
    "daytrade_count",
    "buying_power",
    "cash"
]

def validate_account_for_playbook(account: Dict, fields_to_check: List[str] = None) -> List[str]:
    """
    Pre-flight account validation to ensure the user can execute trades.
    Only checks the provided fields (defaults to global safety fields).
    Returns a list of conflict messages (empty if no conflicts).
    """
    conflicts = []
    fields_to_check = fields_to_check or GLOBAL_ACCOUNT_FIELDS

    if "trading_blocked" in fields_to_check and account.get("trading_blocked"):
        conflicts.append("Account is trading blocked.")

    if "trade_suspended_by_user" in fields_to_check and account.get("trade_suspended_by_user"):
        conflicts.append("Trades suspended by user.")

    if "pattern_day_trader" in fields_to_check and account.get("pattern_day_trader"):
        if "daytrade_count" in fields_to_check and account.get("daytrade_count", 0) >= 3:
            conflicts.append("Pattern Day Trader limit reached.")

    if "buying_power" in fields_to_check and float(account.get("buying_power", 0)) <= 0:
        print("buying_power check", account.get("buying_power", 0))
        conflicts.append("No buying power available.")

    if "cash" in fields_to_check and float(account.get("cash", 0)) <= 0:
        conflicts.append("No cash available.")

    return conflicts
