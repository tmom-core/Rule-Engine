from engine import RuleBlock, RuleCategory
from engine import Primitive, PrimitiveRegistry
from primitives import (
    comparison_evaluator,
    set_membership_evaluator,
    rate_limit_evaluator,
    temporal_gate_evaluator
)

import pandas as pd
import numpy as np
import talib

np.random.seed(42)
minutes = pd.date_range("2026-01-06 09:30", periods=15, freq="T")
price = 100 + np.cumsum(np.random.randn(15))

ohlcv = pd.DataFrame({
    "timestamp": minutes,
    "open": price + np.random.randn(15),
    "high": price + np.random.rand(15),
    "low": price - np.random.rand(15),
    "close": price,
    "volume": np.random.randint(100, 500, size=15)
})
print(ohlcv)




PrimitiveRegistry.register(Primitive("comparison", comparison_evaluator))
PrimitiveRegistry.register(Primitive("set_membership", set_membership_evaluator))
PrimitiveRegistry.register(Primitive("rate_limit", rate_limit_evaluator))
PrimitiveRegistry.register(Primitive("temporal_gate", temporal_gate_evaluator))

entry_skeleton = {
    "extensions": [
        {
            "id": "rsi_ok",
            "primitive": "comparison",
            "params": {
                "indicator": "RSI", # needed for TA-Lib
                "left": "rsi",
                "op": ">",
                "right": 30,
                "timeperiod": 10, # needed for TA-Lib
            }
        },
        {
            "id": "regime_ok",
            "primitive": "set_membership",
            "params": {
                "field": "market_regime",
                "allowed": ["TRENDING", "BREAKOUT"]
            }
        },
        {
            "id": "rate_ok",
            "primitive": "rate_limit",
            "params": {
                "metric": "trades",
                "max": 3,
                "window_minutes": 60
            }
        },
        {
            "id": "time_ok",
            "primitive": "temporal_gate",
            "params": {
                "start_time": 9.5 * 60 * 60,   # 9:30 AM
                "end_time": 11.5 * 60 * 60    # 11:30 AM
            }
        }
    ],
    "conditions": {
        "all": ["rsi_ok", "regime_ok", "rate_ok", "time_ok"]
    }
}

entry_rule = RuleBlock(
    category=RuleCategory.ENTRY,
    skeleton=entry_skeleton
)


ohlcv['rsi'] = talib.RSI(ohlcv['close'], timeperiod=entry_skeleton['extensions'][0]['params']['timeperiod'])



context = {
    "rsi": ohlcv['rsi'].iloc[-1],
    "market_regime": "TRENDING",

    "current_time": 10 * 60 * 60,  # 10:00 AM

    "history": {
        "trades": [
            9.2 * 60 * 60,
            9.6 * 60 * 60
        ]
    }
}

can_enter = entry_rule.evaluate(context)
print("Can enter trade:", can_enter)