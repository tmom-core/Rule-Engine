# rule_parser.py
import json
import uuid
from typing import Optional
from schemas import LLMResponseSchema, RuleSkeletonSchema
from engine import RuleBlock, RuleCategory, Extension
from prompts import build_system_prompt

class RuleParser:
    def __init__(self, llm_client, category: RuleCategory = RuleCategory.ENTRY, max_repairs: int = 2):
        """
        llm_client: your OpenAI / LLM wrapper
        category: the RuleCategory to assign to all parsed rules
        max_repairs: how many times to ask LLM to repair invalid JSON
        """
        self.llm = llm_client
        self.category = category
        self.max_repairs = max_repairs
        self.system_prompt = build_system_prompt()

    def parse(self, user_input: str) -> RuleBlock:
        """
        Parse user input into a RuleBlock ready for engine evaluation.
        """
        full_prompt = self.system_prompt + "\n\nUser input:\n" + user_input
        print(full_prompt)
        raw = self.llm.generate(self.system_prompt, user_input)
        llm_response = self._validate_with_repair(raw)

        if llm_response.status != "ok":
            raise ValueError(f"Cannot parse rule: {llm_response.reason or 'LLM needs clarification'}")

        skeleton_dict = llm_response.rule.dict()
        print("skeleton dict: ", json.dumps(skeleton_dict, indent=2))
        return RuleBlock(category=self.category, skeleton=skeleton_dict)

    def _validate_with_repair(self, raw: str) -> LLMResponseSchema:
        """
        Validate raw JSON from LLM and attempt repair if invalid.
        """
        for attempt in range(self.max_repairs + 1):
            try:
                parsed = json.loads(raw)

                # Normalize missing optional fields
                if "rule" not in parsed:
                    parsed["rule"] = None
                if "reason" not in parsed:
                    parsed["reason"] = None

                # Wrap flat output into rule skeleton if needed
                if parsed.get("rule") is None and "primitive" in parsed:
                    ext_id = parsed.get("id") or f"ext_{uuid.uuid4().hex[:8]}"
                    parsed["rule"] = {
                        "extensions": [
                            {
                                "id": ext_id,
                                "primitive": parsed["primitive"],
                                "params": parsed.get("params", {})
                            }
                        ],
                        "conditions": {"all": [ext_id]}
                    }

                return LLMResponseSchema.model_validate(parsed)

            except Exception as e:
                if attempt >= self.max_repairs:
                    raise ValueError(f"LLM output invalid after repair: {e}")

                # Ask LLM to repair
                raw = self.llm.generate(self.system_prompt,
                    f"""
Previous output failed validation.

Error:
{str(e)}

Return ONLY valid JSON matching schema:
- top-level 'status': 'ok' | 'needs_clarification' | 'unsupported'
- optional 'reason'
- 'rule': {{ "extensions": [{{'id', 'primitive', 'params'}}], "conditions": {{'all', 'any', 'none'}} }}
"""
                )
