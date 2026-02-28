# schemas.py
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field

RuleCategory = Literal["ENTRY", "PROCESS", "RISK", "DISCIPLINE", "EXIT", "OVERRIDES"]
Status = Literal["ok", "needs_clarification", "unsupported"]

class TALibMetricSchema(BaseModel):
    name: str # e.g., 'RSI', 'EMA', 'ATR'
    timeperiod: Optional[int] = None
    params: Optional[Dict[str, float]] = None # For additional parameters like MACD fast/slow periods


class ExtensionSchema(BaseModel):
    id: str
    primitive: str
    params: Dict[str, object]


from typing import List, Dict, Optional, Literal, Union

# ... (rest of imports)

class ConditionsSchema(BaseModel):
    all: Optional[List[Union[str, 'ConditionsSchema']]] = []
    any: Optional[List[Union[str, 'ConditionsSchema']]] = []
    none: Optional[List[Union[str, 'ConditionsSchema']]] = []

# This allows Pydantic to resolve the self-reference
ConditionsSchema.model_rebuild()

class RuleSkeletonSchema(BaseModel):
    name: str # e.g. "Long VWAP Setup", "Max Daily Loss Constraint"
    category: RuleCategory
    extensions: List[ExtensionSchema]
    conditions: Optional[ConditionsSchema] = None


class ContextSkeletonSchema(BaseModel):
    symbol: Optional[str] = None
    market_data: List[str] = []
    ta_lib_metrics: List[TALibMetricSchema] = Field(default_factory=list)
    account_fields: List[str] = []


class LLMResponseSchema(BaseModel):
    status: Status
    rules: List[RuleSkeletonSchema] = Field(default_factory=list)
    context_skeleton: Optional[ContextSkeletonSchema] = Field(default=None)
    reason: Optional[str] = None

