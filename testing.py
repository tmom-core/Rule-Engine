from primitives import *
from engine import Primitive, PrimitiveRegistry, RuleBlock, Extension

PrimitiveRegistry.register(Primitive("comparison", comparison_evaluator))
PrimitiveRegistry.register(Primitive("set_membership", set_membership_evaluator))

print(PrimitiveRegistry.get("comparison").evaluate(
    {'left': 'price', 'right': 100, 'op': '>'},
    {'price': 150}
))  # Expected: True