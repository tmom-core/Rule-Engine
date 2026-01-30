# schemas.py
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field

RuleCategory = Literal["ENTRY", "PROCESS", "RISK", "DISCIPLINE", "EXIT", "OVERRIDES"]
Status = Literal["ok", "needs_clarification", "unsupported"]


class ExtensionSchema(BaseModel):
    id: str
    primitive: str
    params: Dict[str, object]


class ConditionsSchema(BaseModel):
    all: Optional[List[str]] = []
    any: Optional[List[str]] = []
    none: Optional[List[str]] = []


class RuleSkeletonSchema(BaseModel):
    extensions: List[ExtensionSchema]
    conditions: Optional[ConditionsSchema] = None



class ContextSkeletonSchema(BaseModel):
    symbol: Optional[str] = None
    market_data: List[str] = []
    account_fields: List[str] = []
    history_metrics: List[str] = []


class LLMResponseSchema(BaseModel):
    status: Status
    rule: Optional[RuleSkeletonSchema] = Field(default=None)
    context_skeleton: Optional[ContextSkeletonSchema] = Field(default=None)
    reason: Optional[str] = None
