# account_validation.py

from typing import Dict, List

def validate_account_for_playbook(account: Dict) -> List[str]:
    """
    Pre-flight account validation to ensure the user can execute trades.
    Returns a list of conflict messages (empty if no conflicts).
    """
    conflicts = []

    if account.get("trading_blocked"):
        conflicts.append("Account is trading blocked.")
    if account.get("trade_suspended_by_user"):
        conflicts.append("Trades suspended by user.")
    if account.get("pattern_day_trader") and account.get("daytrade_count", 0) >= 3:
        conflicts.append("Pattern Day Trader limit reached.")
    if float(account.get("buying_power", 0)) <= 0:
        conflicts.append("No buying power available.")
    if float(account.get("cash", 0)) <= 0:
        conflicts.append("No cash available.")

    return conflicts
