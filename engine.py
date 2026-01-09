from typing import Any, Dict, List, Callable
from enum import Enum

class RuleCategory(Enum):
    ENTRY = 1
    PROCESS = 2
    RISK = 3
    DISCIPLINE = 3
    EXIT = 4
    OVERRIDES = 5

class Primitive:
    def __init__ (self, name: str, evaluator: Callable[..., bool]):
        self.name = name
        self.evaluator = evaluator

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
        results = {eid: ext.evaluate(context) for eid, ext in self.extensions.items()}
        if "all" in self.conditions:
            if not all(results[eid] for eid in self.conditions["all"]):
                return False
        if "any" in self.conditions:
            if not any(results[eid] for eid in self.conditions["any"]):
                return False
        if "none" in self.conditions:
            if any(results[eid] for eid in self.conditions["none"]):
                return False
        return True
    

