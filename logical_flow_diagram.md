# Rule Engine – Logical Component Diagram Descriptions

![alt text](image-1.png)

## Layer 1: Rule Authoring & Input

**User / Trader Input**  
Source of trading rules. Rules may be provided as natural language, structured UI input, or a domain-specific language (DSL).

**Rule Parser / LLM**  
Interprets user input and extracts structured intent, mapping it to known rule concepts and primitives.

**Rule Skeleton Generator**  
Transforms parsed intent into a canonical rule skeleton composed of predefined rule categories (entry, risk, discipline) and registered primitives.

---

## Layer 2: Validation & Safety

**Schema Validator**  
Verifies the structural correctness of the rule skeleton: required fields exist, types are valid, primitives are supported, and references are well-formed.

**Primitive Registry**  
Central registry defining all supported primitives, including their required inputs, evaluation semantics, and constraints.

**Conflict Detector**  
Analyzes the rule skeleton for logical contradictions or incompatible rules (e.g., mutually exclusive conditions or impossible constraints).

**Global Safety Rules**  
System-wide, non-negotiable guardrails enforced regardless of user configuration (e.g., hard risk caps, regulatory limits, trading halts).

---

## Layer 3: Context Hydration

**Context Builder**  
Aggregates live account data, system state, real-time market data, and computes derived metrics required for rule evaluation.

**Immutable Evaluation Context**  
A read-only snapshot of all inputs and derived metrics used during evaluation, ensuring deterministic behavior and auditability.

**Rule Engine Orchestrator**  
Coordinates the evaluation process by invoking evaluators, resolving dependencies, and managing evaluation order.

---

## Layer 4: Rule Evaluation Engine

**Primitive Evaluators**  
Execute individual primitives against the evaluation context and return boolean or numeric results.

**Constraint Resolver**  
Combines primitive results according to rule logic (AND/OR/thresholds) to determine whether constraints are satisfied.

**FSM State Resolver**  
Evaluates stateful rules by resolving finite-state transitions based on historical behavior and prior outcomes.

**Rule Outcome**  
Final normalized decision produced by the engine (e.g., allow, block, warn, enforce), including supporting metadata.

---

## Layer 5: Enforcement & Feedback

**Trade Gate / Broker Adapter**  
Enforces rule outcomes at execution time by sending a notification to the user advising them on what to do or what not to do given the current market data.

**Violation Logger**  
Records rule violations, decisions, and supporting context for auditing, replay, and compliance.

**Deviation Cost Analyzer**  
Quantifies the financial and behavioral cost of deviations from defined trading rules.

**User Feedback / Alerts**  
Communicates decisions, warnings, and explanations to the user in real time or post-trade.

## Cmponents that are Not Implemented
- **Global Safety Rules**
    - No explicit system-wide, non-user-configurable constraints exist yet.
    - These are currently assumed or “left to account limits.”

- **Rule Engine Orchestrator**
    - Evaluation likely happens inline or procedurally.
    - There is no centralized controller managing evaluation phases.
- **Constraint Resolver**
    - Constraints are likely evaluated ad hoc.
    - No formal logic layer that combines primitive results into rule-level decisions.
    - There are multiple sources of constraints and this constrain resolver will tell us in which gives precedence.
    - For example, BLOCK > MODIFY > ALLOW.
    - Given all rules and modes, which one takes precedence.
- **FSM / State Resolver**
    - Stateful enforcement (cooldowns, repeated violations, escalation) is not implemented.
    - No explicit state machine driving rule transitions over time.
    - What is the last known state and what to do from there.
