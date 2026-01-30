# primitives.py
from typing import Dict, Any

# ---------------------------
# Core Primitive Evaluators
# ---------------------------

# Change as needed as this is recommendation from GPT
# Might need Satya knowledge on this LOL

def comparison_evaluator(params: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """Evaluates comparison between a context value (left) and a constant (right)."""
    left = context.get(params['left'], 0)
    right = params['right']
    op = params['op']

    if op == '>':
        return left > right
    elif op == '<':
        return left < right
    elif op == '==':
        return left == right
    elif op == '>=':
        return left >= right
    elif op == '<=':
        return left <= right
    else:
        raise ValueError(f"Unknown operator {op}")


def set_membership_evaluator(params: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """Checks if a context value is within allowed set or excludes forbidden set."""
    value = context.get(params['field'])
    allowed = params.get('allowed', [])
    forbidden = params.get('forbidden', [])

    if allowed and value not in allowed:
        return False
    if forbidden and value in forbidden:
        return False
    return True


def rate_limit_evaluator(params: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """Checks if event count within a time window exceeds a limit."""
    metric = params['metric']
    max_count = params['max']
    window_minutes = params['window_minutes']

    history = context.get('history', {}).get(metric, [])  # list of timestamps
    current_time = context.get('current_time')

    count_in_window = sum(1 for t in history if current_time - t <= window_minutes * 60)
    return count_in_window <= max_count


def accumulation_evaluator(params: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """Evaluates if an accumulated metric (e.g. daily loss) meets a threshold."""
    field = params['field']
    threshold = params['threshold']
    op = params.get('op', '>=')

    total = context.get(field, 0)

    if op == '>=':
        return total >= threshold
    elif op == '<=':
        return total <= threshold
    elif op == '>':
        return total > threshold
    elif op == '<':
        return total < threshold
    elif op == '==':
        return total == threshold
    else:
        raise ValueError(f"Unknown operator {op}")


def sequence_evaluator(params: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """
    Detects if a specific sequence of events occurred directly in history.
    Optionally constrained by a time window.
    """
    pattern = params['pattern']
    window_minutes = params.get('window_minutes', 0)

    events = context.get('event_history', [])
    if window_minutes:
        current_time = context.get('current_time')
        events = [(t, e) for t, e in events if current_time - t <= window_minutes * 60]

    events_only = [e for _, e in events]
    pattern_index = 0

    for e in events_only:
        if e == pattern[pattern_index]:
            pattern_index += 1
            if pattern_index == len(pattern):
                return True

    return False


def temporal_gate_evaluator(params: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """Evaluates if current time is within allowed window or past a cooldown."""
    current_time = context.get('current_time')

    start = params.get('start_time')
    end = params.get('end_time')

    if start and end:
        return start <= current_time <= end

    cooldown_end = params.get('cooldown_end')
    if cooldown_end:
        return current_time >= cooldown_end

    return True

def account_comparison_evaluator(params: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """
    Evaluates a comparison against a broker account field.

    Example params:
    {
        "field": "buying_power",
        "op": ">=",
        "value": 50000
    }

    Requires that `context` contains an "account" dict with the relevant field.
    """
    account = context.get("account", {})
    
    field = params["field"]
    op = params["op"]
    value = params["value"]

    if field not in account:
        raise ValueError(f"Account field '{field}' not available in context")
    if isinstance(value, str) and not any(c.isalpha() for c in value):
        value = float(value)
    elif isinstance(value, (int, float)):
        pass
    else:
        pass

    # If value is explicitly None (e.g. LLM failed to resolve), we cannot compare.
    if value is None:
        print(f"WARNING: account_comparison_evaluator received None for 'value' on field '{field}'. Returning False.")
        return False

    # Simplified logic to match intent safely:
    if isinstance(value, str):
         if not any(c.isalpha() for c in value):
             value = float(value)
         else:
             # Fallback to original behavior for string with alphas, though suspicious
             value = account.get('value', 0) # protecting against KeyError if 'value' missing
    # if it's int/float, leave it as is.


    account_value = float(account[field])

    if op == ">":
        return account_value > value
    elif op == ">=":
        return account_value >= value
    elif op == "<":
        return account_value < value
    elif op == "<=":
        return account_value <= value
    elif op == "==":
        return account_value == value
    else:
        raise ValueError(f"Unknown operator '{op}' in account_comparison")
