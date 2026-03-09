# Rule Engine & Frontend Data Integration Flow

This document outlines how a user's natural language trading strategy is parsed by the LLM into a strict JSON schema, how data requirements are communicated to the frontend, and how the frontend is expected to stream that data back to the backend execution engine.

## 1. The Parsing Flow

When a user creates a new strategy playbook, the following sequence occurs:

1. **User Input:** The user submits a natural-language trading rule (e.g., *"Buy AAPL if RSI > 30 and the 5-minute volume is high"*).
2. **LLM Translation:** The backend LLM parses this rule against a strict set of constraints. It breaks the rule down into logical blocks (Conditions and Extensions) and identifies every single piece of data needed to evaluate that rule.
3. **Context Skeleton Generation:** The LLM generates a `context_skeleton`—a list of exact data dependencies required to run the strategy.
4. **Handoff to Frontend:** The backend sends this `context_skeleton` to the frontend so the frontend knows exactly what market data and indicators to subscribe to and stream back.
5. **Evaluation Loop:** As the frontend streams the requested data over the WebSocket, the backend Engine (`execution_engine.py`) takes that stream, securely fetches the requested Account data from Alpaca, and evaluates the playbook.

---

## 2. LLM Engine Limitations & Constraints

To ensure the engine remains deterministic and doesn't crash on undefined data, the LLM parser is heavily constrained:

* **No Invented Fields:** The LLM cannot invent metric names. It cannot ask for `"last_5m_candle_max"` or `"custom_momentum_oscillator"`. It must strictly select from the predefined arrays listed below.
* **No Dummy Account Metrics:** If a rule implies checking recent trade history (e.g., "max 5 trades today"), it cannot invent `"daily_trade_count"`. It must request the underlying foundational account field (e.g., `"daytrade_count"`).
* **Strict TA-Lib Parameters:** The LLM can only request valid technical indicators from a predefined JSON metadata dictionary mapping directly to the C/Python TA-Lib library, respecting exact parameter names and types.
* **Graceful Degradation:** If the user asks for data the engine does not support, the LLM is instructed to reject the rule and return `status = "unsupported"` rather than hallucinating an unsupported data field.

---

## 3. Allowed Data Selection Arrays

The LLM builds its data requirements by selecting **only** from the following lists:

### A. Core Market Data Fields
If the rule depends on raw price or volume action, the LLM selects from this exact list:
```json
[
  "price", "bid", "ask", "volume", "vwap",
  
  "open_1m", "high_1m", "low_1m", "close_1m", "volume_1m",
  "prior_candle_high_1m", "prior_candle_low_1m",
  
  "open_5m", "high_5m", "low_5m", "close_5m", "volume_5m",
  "prior_candle_high_5m", "prior_candle_low_5m",
  
  "open_15m", "high_15m", "low_15m", "close_15m", "volume_15m",
  "open_1h", "high_1h", "low_1h", "close_1h", "volume_1h",
  "open_1d", "high_1d", "low_1d", "close_1d", "volume_1d",
  
  "high_of_day", "low_of_day", "open_of_day"
]
```

### B. Account Data Fields (Handled by Backend)
If the rule's threshold depends on a live account value (e.g., "Risk 1% of equity"), the LLM requests these fields. **Note: The frontend does not provide these; the backend fetches them directly from the broker.**
```json
[
  "account_blocked", "account_number", "accrued_fees", "buying_power", "cash",
  "created_at", "crypto_status", "currency", "daytrade_count", "daytrading_buying_power",
  "equity", "id", "initial_margin", "last_equity", "last_maintenance_margin",
  "long_market_value", "maintenance_margin", "multiplier", "non_marginable_buying_power",
  "options_approved_level", "options_buying_power", "options_trading_level",
  "pattern_day_trader", "portfolio_value", "regt_buying_power",
  "short_market_value", "shorting_enabled", "sma", "status",
  "trade_suspended_by_user", "trading_blocked", "transfers_blocked"
]
```

### C. TA-Lib Technical Indicators
The LLM can request hundreds of technical indicators. It builds an array of required metrics, specifying the `name` (e.g., "RSI"), the `timeperiod` (e.g., 14), and any specific calculation parameters.

---

## 4. The Data Contract Example

Below is an example of the interaction between the Backend LLM Output and the expected Frontend Stream Input.

### Step 1: LLM Context Skeleton (Sent to Frontend)
When the LLM finishes parsing, it saves a `context_skeleton` to the database. The frontend reads this to know what data the engine needs to function.

```json
{
  "symbol": "BTC",
  "market_data": [
    "price",
    "volume_5m",
    "vwap"
  ],
  "ta_lib_metrics": [
    {
      "name": "RSI",
      "timeperiod": 14
    },
    {
      "name": "EMA",
      "timeperiod": 20
    }
  ],
  "account_fields": [
    "buying_power",
    "daytrade_count"
  ]
}
```

### Step 2: Frontend Data Stream Payload (Sent back to Engine)
Based on the skeleton above, the frontend must stream the requested `market_data` and `ta_lib_metrics` over the WebSocket. 

**Critical Formatting Rule:** TA-Lib metrics must be passed as `"NAME_timeperiod"` (e.g., `"RSI_14"`). If no `timeperiod` is specified by the metric, just pass `"NAME"`.

```json
{
  // 1. Core Fields (Always Required)
  "symbol": "BTC",
  "current_time": "2023-10-27T14:30:00Z",
  "price": 34500.50,
  
  // 2. Specific market_data requested by the skeleton
  "volume_5m": 1250,
  "vwap": 34480.20,
  
  // 3. Specific ta_lib_metrics requested by the skeleton
  "RSI_14": 55.25,
  "EMA_20": 34200.00,

  // 4. Specific account_fields requested by the skeleton
  "buying_power": 10000.00,
  "daytrade_count": 2
}
```

---

## 5. TA-Lib Metrics Class Structure

When the LLM requests technical indicators, it uses the `TALibMetricSchema` definition. The frontend team will receive objects structured like this inside the `context_skeleton.ta_lib_metrics` array:

```python
class TALibMetricSchema(BaseModel):
    name: str # e.g., 'RSI', 'EMA', 'ATR'
    timeperiod: Optional[int] = None
    params: Optional[Dict[str, float]] = None # For additional parameters like MACD fast/slow periods
```

### Explanation of Fields:

1. **`name` (Required)** 
   - A strict string matching a valid TA-Lib function (e.g., `"RSI"`, `"MACD"`, `"BBANDS"`). 
   - The LLM will only output uppercase names that exactly match the supported TA-Lib metadata dictionary.
   
2. **`timeperiod` (Optional)** 
   - An integer representing the lookback period (e.g., `14` for a 14-period RSI). 
   - Not all indicators use a timeperiod (e.g., MACD uses specific fast/slow periods instead).

3. **`params` (Optional)** 
   - A dictionary for indicators that require multiple specific configuration parameters.
   - For example, if the LLM requests the MACD indicator, the frontend might receive:
     ```json
     {
       "name": "MACD",
       "params": {
         "fastperiod": 12,
         "slowperiod": 26,
         "signalperiod": 9
       }
     }
     ```

### Example of the TA-Lib Metric Dataset Used by LLM
```json
"MININDEX": {
    "group": "Math Operators",
    "display_name": "Index of lowest value over a specified period",
    "inputs": {},
    "parameters": {
      "timeperiod": 30
    },
    "outputs": []
  },
  "MINMAX": {
    "group": "Math Operators",
    "display_name": "Lowest and highest values over a specified period",
    "inputs": {},
    "parameters": {
      "timeperiod": 30
    },
    "outputs": []
  },
  "MINMAXINDEX": {
    "group": "Math Operators",
    "display_name": "Indexes of lowest and highest values over a specified period",
    "inputs": {},
    "parameters": {
      "timeperiod": 30
    },
    "outputs": []
  },
  "MULT": {
    "group": "Math Operators",
    "display_name": "Vector Arithmetic Mult",
    "inputs": {},
    "parameters": {},
    "outputs": []
  },
  "SUB": {
    "group": "Math Operators",
    "display_name": "Vector Arithmetic Subtraction",
    "inputs": {},
    "parameters": {},
    "outputs": []
  },
  "SUM": {
    "group": "Math Operators",
    "display_name": "Summation",
    "inputs": {},
    "parameters": {
      "timeperiod": 30
    },
    "outputs": []
  },
  "ACOS": {
    "group": "Math Transform",
    "display_name": "Vector Trigonometric ACos",
    "inputs": {},
    "parameters": {},
    "outputs": []
  },
  "ASIN": {
    "group": "Math Transform",
    "display_name": "Vector Trigonometric ASin",
    "inputs": {},
    "parameters": {},
    "outputs": []
  },
  "ATAN": {
    "group": "Math Transform",
    "display_name": "Vector Trigonometric ATan",
    "inputs": {},
    "parameters": {},
    "outputs": []
  },
  "CEIL": {
    "group": "Math Transform",
    "display_name": "Vector Ceil",
    "inputs": {},
    "parameters": {},
    "outputs": []
  },
  "COS": {
    "group": "Math Transform",
    "display_name": "Vector Trigonometric Cos",
    "inputs": {},
    "parameters": {},
    "outputs": []
  },
  "COSH": {
    "group": "Math Transform",
    "display_name": "Vector Trigonometric Cosh",
    "inputs": {},
    "parameters": {},
    "outputs": []
  },
  "EXP": {
    "group": "Math Transform",
    "display_name": "Vector Arithmetic Exp",
    "inputs": {},
    "parameters": {},
    "outputs": []
  },
  "FLOOR": {
    "group": "Math Transform",
    "display_name": "Vector Floor",
    "inputs": {},
    "parameters": {},
    "outputs": []
  },
  "LN": {
    "group": "Math Transform",
    "display_name": "Vector Log Natural",
    "inputs": {},
    "parameters": {},
    "outputs": []
  },
  "LOG10": {
    "group": "Math Transform",
    "display_name": "Vector Log10",
    "inputs": {},
    "parameters": {},
    "outputs": []
  },
```

### Constructing the WebSocket Key:
When the frontend calculates the value for a requested TA-Lib metric, it MUST construct the JSON key for the WebSocket payload using the exact rule:
* If `timeperiod` is present: `"{name}_{timeperiod}"` (e.g., `"RSI_14"`)
* If `timeperiod` is absent: `"{name}"` (e.g., `"MACD"`)

The backend engine's evaluator primitives use this specific combined string identifier to look up the indicator value in the market context payload.
