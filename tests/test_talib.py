import sys
import os
import json
import asyncio
from dotenv import load_dotenv

# Add project root to path (one directory up from llm_layer)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_layer.openai_client import OpenAILLMClient
from llm_layer.rule_parser import RuleParser
from engine import RuleCategory, PrimitiveRegistry, Primitive
from primitives import comparison_evaluator, sequence_evaluator

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(env_path)

# Register minimal primitives needed for parsing
if "comparison" not in PrimitiveRegistry._registry:
    PrimitiveRegistry.register(
        Primitive("comparison", comparison_evaluator)
    )

if "sequence" not in PrimitiveRegistry._registry:
    PrimitiveRegistry.register(
        Primitive("sequence", sequence_evaluator)
    )

async def test_talib_extraction():
    llm_client = OpenAILLMClient(model="gpt-4.1")
    parser = RuleParser(llm_client, category=RuleCategory.ENTRY)
    
    test_prompts = [
        "Buy if RSI(14) > 30 and EMA(20) > SMA(50)",
        "Sell if price < VWAP and MACD(12, 26, 9) crosses below 0"
    ]
    
    print("Testing TA-Lib extraction with RuleParser...\n")
    for prompt in test_prompts:
        print(f"=== Prompt: '{prompt}' ===")
        try:
            playbook, context_skeleton = parser.parse(prompt)
            print("\nExtracted Context Skeleton:")
            print(json.dumps(context_skeleton.dict(), indent=2))
            
            print("\nExtracted TA-Lib Metrics:")
            if context_skeleton.ta_lib_metrics:
                for metric in context_skeleton.ta_lib_metrics:
                    print(f"  - {metric.name} (period: {metric.timeperiod}, params: {metric.params})")
            else:
                print("  (None extracted)")
            print("-" * 40)
        except Exception as e:
            print(f"Error parsing: {e}")

if __name__ == "__main__":
    asyncio.run(test_talib_extraction())
