# engine.py
from typing import Any, Dict, List, Callable
from enum import Enum
from account_validation import validate_account_for_playbook


class RuleCategory(Enum):
    """Enumeration of available trading rule categories."""
    ENTRY = 1
    PROCESS = 2
    RISK = 3
    DISCIPLINE = 3
    EXIT = 4
    OVERRIDES = 5


class Primitive:
    """
    Base unit of logic for the rule engine.
    Wraps an evaluator function and defines its data requirements.
    """
    def __init__(
        self,
        name: str,
        evaluator: Callable[..., bool],
        required_context: List[str] = None,
        required_account_fields: List[str] = None
    ):
        self.name = name
        self.evaluator = evaluator
        self.required_context = required_context or []
        self.required_account_fields = required_account_fields or []

    def evaluate(self, params: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Executes the primitive's logic against the provided parameters and context."""
        return self.evaluator(params, context)


class PrimitiveRegistry:
    """Global registry for all available primitives."""
    _registry: Dict[str, Primitive] = {}

    @classmethod
    def register(cls, primitive: Primitive):
        """Registers a new primitive."""
        cls._registry[primitive.name] = primitive

    @classmethod
    def get(cls, name: str) -> Primitive:
        """Retreives a primitive by name."""
        if name not in cls._registry:
            raise ValueError(f"Primitive '{name}' not found in registry.")
        return cls._registry[name]


class Extension:
    """
    A concrete instance of a primitive configured with specific parameters.
    Represents a single logical check (e.g., 'RSI > 30').
    """
    def __init__(self, primitive_name: str, params: Dict[str, Any], ext_id: str):
        self.primitive_name = primitive_name
        self.params = params
        self.id = ext_id
        self.primitive = PrimitiveRegistry.get(primitive_name)

        for key in params:
            if key in ["field", "fields"]:
                if isinstance(params[key], list):
                    self.primitive.required_account_fields.extend(params[key])
                else:
                    self.primitive.required_account_fields.append(params[key])
        
        self.primitive.required_account_fields = list(set(self.primitive.required_account_fields))

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """Evaluates this specific extension instance."""
        return self.primitive.evaluate(self.params, context)


class ContextBuilder:
    """
    Responsible for assembling the full data context (Market + Account) required for evaluation.
    """
    def __init__(self, account_provider, user_action_provider=None, global_account_fields: List[str] = None):
        self.account_provider = account_provider
        self.user_action_provider = user_action_provider
        self.global_account_fields = set(global_account_fields or [])

    def hydrate(self, base_context: Dict[str, Any], context_skeleton=None, extensions: List['Extension'] = None) -> Dict[str, Any]:
        """
        Build full evaluation context including market data, account snapshot, and user action history.
        Fetches only the specific account fields and history metrics requested by the Context Skeleton.
        """
        dynamic_account_fields = set()
        history_metrics = []

        if context_skeleton:
            dynamic_account_fields.update(context_skeleton.account_fields)
            history_metrics = context_skeleton.history_metrics
        elif extensions:
            for ext in extensions:
                if "field" in ext.params:
                    dynamic_account_fields.add(ext.params["field"])
        
        all_fields = dynamic_account_fields.union(self.global_account_fields)
        
        context = dict(base_context)
        
        # 1. Account Data
        if all_fields:
            account_snapshot = self.account_provider.get_snapshot(list(all_fields))
            context["account"] = account_snapshot
            
        # 2. History / User Actions
        if self.user_action_provider and history_metrics:
            history_context = self.user_action_provider.get_history(history_metrics)
            # Merge into a top-level 'history' key or however primitives expect it
            # primitives.py expects context.get('history', {}).get(metric, [])
            context["history"] = history_context

        return context


class RuleBlock:
    """
    A collection of Extensions (logic units) and Conditions (logic gates) 
    that functions as a complete, evaluatable rule.
    """
    def __init__(self, category: RuleCategory, skeleton: Dict[str, Any]):
        self.category = category
        self.extensions: Dict[str, Extension] = {}
        self.conditions: Dict[str, List[str]] = skeleton.get("conditions", {})
        self._load_extensions(skeleton.get("extensions", []))

    def _load_extensions(self, extensions: List[Dict[str, Any]]):
        """Instantiates Extension objects from the JSON skeleton."""
        for ext in extensions:
            extension = Extension(ext["primitive"], ext["params"], ext["id"])
            self.extensions[extension.id] = extension

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluates the entire rule block.
        1. Checks global account safety constraints.
        2. Evaluates all extensions.
        3. Applies boolean logic (ALL/ANY/NONE) to extension results.
        """
        account = context.get("account")
        if account:
            conflicts = validate_account_for_playbook(account)
            if conflicts:
                print("ACCOUNT CONFLICTS DETECTED:", conflicts)
                return False

        results = {eid: ext.evaluate(context) for eid, ext in self.extensions.items()}

        all_ids = self.conditions.get("all", [])
        any_ids = self.conditions.get("any", [])
        none_ids = self.conditions.get("none", [])

        if all_ids and not all(results[eid] for eid in all_ids):
            return False
        if any_ids and not any(results[eid] for eid in any_ids):
            return False
        if none_ids and any(results[eid] for eid in none_ids):
            return False

        return True


class RuleConflictChecker:
    """
    Static analyzer to check if a rule's parameters conflict with the current account state
    BEFORE evaluation (e.g., checking if the rule requires more buying power than available).
    """
    def __init__(self, account_snapshot: Dict[str, Any]):
        self.account = account_snapshot

    def check_conflict(self, extension) -> List[str]:
        """Checks a single extension for logical conflicts with account state."""
        conflicts = []
        if extension.primitive.name == "account_comparison":
            field = extension.params["field"]
            op = extension.params["op"]
            value = extension.params["value"]
            account_value = self.account.get(field)

            if account_value is None:
                conflicts.append(f"Account field {field} missing")
            else:
                if op in [">", ">="] and value > account_value:
                    conflicts.append(f"Rule requires {field} >= {value}, but account has {account_value}")
                elif op in ["<", "<="] and value < account_value:
                    conflicts.append(f"Rule requires {field} <= {value}, but account has {account_value}")
                elif op == "==" and value != account_value:
                    conflicts.append(f"Rule requires {field} == {value}, but account has {account_value}")
        return conflicts

    def validate_rule_block(self, rule_block) -> List[str]:
        """Checks entire rule block for conflicts."""
        all_conflicts = []
        for ext in rule_block.extensions.values():
            all_conflicts.extend(self.check_conflict(ext))
        return all_conflicts
