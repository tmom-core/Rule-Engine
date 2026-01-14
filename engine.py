from typing import Any, Dict, List, Callable
from enum import Enum
from account_validation import validate_account_for_playbook

class RuleCategory(Enum):
    ENTRY = 1
    PROCESS = 2
    RISK = 3
    DISCIPLINE = 3
    EXIT = 4
    OVERRIDES = 5

class Primitive:
    def __init__(
        self, 
        name: str, 
        evaluator: Callable[..., bool], 
        required_context: list[str] = None,          # new
        required_account_fields: list[str] = None   # new
    ):
        self.name = name
        self.evaluator = evaluator
        self.required_context = required_context or []          # market / event data
        self.required_account_fields = required_account_fields or []  # account fields

    def evaluate(self, params: Dict[str, Any], context: Dict[str, Any]) -> bool:
        return self.evaluator(params, context)

    

class PrimitiveRegistry:
    _registry: Dict[str, Primitive] = {}

    @classmethod
    def register(cls, primitive: Primitive):
        cls._registry[primitive.name] = primitive

    @classmethod
    def get(cls, name: str) -> Primitive:
        if name not in cls._registry:
            raise ValueError(f"Primitive '{name}' not found in registry.")
        return cls._registry[name]

class Extension:
    def __init__(self, primitive_name: str, params: Dict[str, Any], ext_id: str):
        self.primitive_name = primitive_name
        self.params = params
        self.id = ext_id
        self.primitive = PrimitiveRegistry.get(primitive_name)

    def evaluate(self, context: Dict[str, Any]) -> bool:
        return self.primitive.evaluate(self.params, context)
    
class ContextBuilder:
    def __init__(self, account_provider, global_account_fields: List[str] = None):
        self.account_provider = account_provider
        self.global_account_fields = global_account_fields or []

    def hydrate(self, base_context: Dict[str, Any], primitives: List[Primitive]) -> Dict[str, Any]:
        # Collect all account fields required by primitives
        required_account_fields = set()
        for p in primitives:
            required_account_fields.update(p.required_account_fields)

        # Include global safety fields
        all_fields = required_account_fields.union(self.global_account_fields)

        context = dict(base_context)

        if all_fields:
            account_snapshot = self.account_provider.get_snapshot(list(all_fields))
            context["account"] = account_snapshot  # Inject account data

        return context

    
class RuleBlock:
    def __init__(self, category: RuleCategory, skeleton: Dict[str, Any]):
        self.category = category
        self.extensions: Dict[str, Extension] = {}
        self.conditions: Dict[str, List[str]] = skeleton.get("conditions", [])
        self._load_extensions(skeleton.get("extensions", []))

    def _load_extensions(self, extensions: List[Dict[str, Any]]):
        for ext in extensions:
            extension = Extension(ext["primitive"], ext["params"], ext["id"])
            self.extensions[extension.id] = extension

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """
        Evaluate rule block with pre-flight account validation.
        Stops evaluation if account conflicts are detected.
        """
        account = context.get("account")
        if account:
            conflicts = validate_account_for_playbook(account)
            if conflicts:
                print("ACCOUNT CONFLICTS DETECTED:", conflicts)
                return False                                     

        results = {eid: ext.evaluate(context) for eid, ext in self.extensions.items()}
        if "all" in self.conditions and not all(results[eid] for eid in self.conditions["all"]):
            return False
        if "any" in self.conditions and not any(results[eid] for eid in self.conditions["any"]):
            return False
        if "none" in self.conditions and any(results[eid] for eid in self.conditions["none"]):
            return False
        return True

    

class RuleConflictChecker:
    def __init__(self, account_snapshot: Dict[str, Any]):
        self.account = account_snapshot

    def check_conflict(self, extension) -> List[str]:
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
        all_conflicts = []
        for ext in rule_block.extensions.values():
            all_conflicts.extend(self.check_conflict(ext))
        return all_conflicts
