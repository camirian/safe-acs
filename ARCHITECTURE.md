# ARCHITECTURE.md

## Executive Summary
The Cyber-Physical AI Assurance Framework (SafeACS) integrates Anthropic's steerable AI models (Claude) with mission-critical cyber-physical systems via an NVIDIA Jetson Orin Nano edge-compute node. Designed to operate within zero-requirements-drift aerospace constraints, SafeACS enforces deterministic safety boundaries using auto-generated Pydantic guardrails derived directly from SysML v2 property blocks. This architecture ensures all heuristic anomalies detected by Claude are verified against hard structural limits in under 50ms at the edge, maintaining absolute safety, bidirectionally traceable compliance, and auditable proof of innocence before any control action reaches the Satellite Attitude Control System.

## C4 Model Architecture Topologies

> [!NOTE] 
> **How to Read these Diagrams:**
> These diagrams represent **Data Flow & Structural Boundary Enforcement Topologies**, not state machines. They map the left-to-right flow of physical telemetry data as it passes through deterministic edge constraints, gets analyzed by a probabilistic heuristic engine (Claude), and is finally routed as a verified control action. Follow the directional arrows `--->` to trace the blast radius of any given signal.

### Context Level (Macro System Boundaries)
```mermaid
flowchart LR
    operator(("Flight Operator / Verifier<br>[Person]"))
    satellite_acs["Satellite ACS (Sim)<br>[Software System]"]
    claude_api["Claude API<br>[Software System]"]
    
    safeacs("SafeACS AI Assurance Framework<br>[Software System]")

    satellite_acs --->|"Sends telemetry streams"| safeacs
    safeacs --->|"Sends verified control adjustments"| satellite_acs
    safeacs --->|"Requests heuristic analysis"| claude_api
    claude_api --->|"Returns anomaly detection results"| safeacs
    operator --->|"Approves/Rejects Type 1 Actions"| safeacs
    
    classDef person fill:#08427b,color:#fff,stroke:#052e56
    classDef system fill:#1168bd,color:#fff,stroke:#0b4884
    classDef ext_system fill:#999999,color:#fff,stroke:#8a8a8a
    
    class operator person
    class safeacs system
    class satellite_acs,claude_api ext_system
```
> **Interpretation (Context Level):**
> 1. Raw synthetic state data originates on the left (`Satellite ACS`).
> 2. It hits the `SafeACS` boundary where structural sanity checks occur.
> 3. `SafeACS` offloads anomaly detection to the `Claude API` (right).
> 4. If the LLM proposes an irreversible action, `SafeACS` halts and demands manual `Flight Operator` clearance.

### Container Level (Edge Execution Engine)
```mermaid
flowchart LR
    subgraph jetson_orin [NVIDIA Jetson Orin Nano / Edge Node]
        direction TB
        telemetry_gateway("API Gateway / Receiver<br>[Container: Python]")
        guardrail_layer("Deterministic Guardrails<br>[Container: Pydantic / Python]")
        decision_router("Decision Protocol Router<br>[Container: Python]")
        audit_logger("DR-AIS Logging Engine<br>[Container: Python]")
        
        telemetry_gateway --->|"Parsed Telemetry"| guardrail_layer
        guardrail_layer --->|"Validated State"| decision_router
        decision_router --->|"Action Verification"| guardrail_layer
        decision_router --->|"Records State & Decision"| audit_logger
    end

    claude_api["Claude API (Cloud)<br>[External System]"]
    sim_engine["Synthetic ACS<br>[External System]"]
    ui["Streamlit Dashboard<br>[External System]"]

    sim_engine --->|"Raw State (JSON)"| telemetry_gateway
    guardrail_layer --->|"Authorized Command<br>(Type 2)"| sim_engine
    
    decision_router --->|"Context Prompt<br>(if valid)"| claude_api
    claude_api --->|"Proposed Action"| decision_router
    
    decision_router --->|"Requires Approval<br>(Type 1)"| ui

    classDef container fill:#438dd5,color:#fff,stroke:#3c7fc0
    classDef ext_system fill:#999999,color:#fff,stroke:#8a8a8a
    classDef boundary fill:none,stroke:#444,stroke-width:2px,stroke-dasharray: 5 5
    
    class telemetry_gateway,guardrail_layer,decision_router,audit_logger container
    class claude_api,sim_engine,ui ext_system
    class jetson_orin boundary
```
> **Interpretation (Container Level):**
> This isolates the NVIDIA Jetson Orin Edge Node logic.
> 1. **Signal Ingestion:** Telemetry enters the `API Gateway`.
> 2. **The Hard Boundary:** It immediately passes through `Deterministic Guardrails` (Pydantic constraints compiled from SysML). This is the zero-drift barrier.
> 3. **The Heuristic Pathway:** Valid data is routed by the `Decision Protocol Router` to the `Claude API` for context-aware inference.
> 4. **Bimodal Actuation:** Claude returns a proposed action. The router validates it against the Guardrails again. Reversible actions (Type 2) are passed to the hardware; irreversible actions (Type 1) require UI approval. All state is committed to the `DR-AIS` immutable log.

### System Behavior: The Bimodal Decision Protocol
To understand how SafeACS handles nominal versus critical AI interventions, trace the execution sequence below. This demonstrates how the deterministic edge strictly bounds the probabilistic LLM.

```mermaid
%%{init: {'theme': 'neutral', 'themeVariables': { 'altBackground': 'rgba(220, 235, 255, 0.5)', 'actorLineColor': '#1168bd'}}}%%
sequenceDiagram
    autonumber
    
    participant Sim as Synthetic ACS
    participant Edge as API & Guardrail
    participant Router as Decision Router
    participant Log as DR-AIS Log
    participant Claude as Claude API (Cloud)
    participant Human as Flight Operator
    
    Sim->>Edge: Emit Telemetry Signal (ItemFlow)
    Edge->>Edge: Evaluate Constraint (Attribute Usage: RPM ≤ 6000)
    
    alt if [RPM > 6000] (Fatal Violation)
        Note right of Edge: TOP OPERAND executes<br/>Guard [RPM > 6000] = TRUE<br/>Constraint violated. Hardware at risk.
        Edge-->>Sim: Return: Immediate Safe-Mode PID Override
        Edge->>Log: Signal: Record Constraint Violation
    else else [RPM ≤ 6000] (Nominal State)
        Note right of Edge: BOTTOM OPERAND executes<br/>Guard [RPM > 6000] = FALSE<br/>Constraint satisfied. Proceed to AI layer.
        Edge->>Router: Signal: Pass State to AI Router
    end
    
    Router->>Claude: Signal: Heuristic Context Request
    Claude-->>Router: Return: Proposed Control Action
    
    Router->>Edge: Evaluate Constraint (Proposed Action vs Attribute Bounds)
    
    alt if [Action out-of-bounds]
        Note right of Edge: TOP OPERAND executes<br/>LLM proposed action exceeds structural limits.<br/>Action rejected. Violation logged.
        Edge-->>Router: Return: Reject Action
        Router->>Log: Signal: Record LLM Hallucination/Violation
    else else [Action within bounds]
        Note right of Router: BOTTOM OPERAND executes<br/>Guard [Action out-of-bounds] = FALSE<br/>Action within bounds. Proceed to actuation routing.
        alt if [Type 2: Reversible / Software]
            Note right of Router: TOP OPERAND executes<br/>Reversible action: autonomous execution permitted.
            Router->>Sim: Signal: Autonomous Actuation
            Router->>Log: Signal: Record Type 2 Success
        else else [Type 1: Irreversible / Hardware]
            Note right of Router: BOTTOM OPERAND executes<br/>Irreversible action: human approval required.<br/>Claude is blocked from hardware until operator signs off.
            Router->>Human: Signal: Request Cryptographic Approval
            Human-->>Router: Return: Approve Action
            Router->>Sim: Signal: Verified Actuation
            Router->>Log: Signal: Record Type 1 Human-in-Loop Success
        end
    end
```
> **Interpretation (SysML v2 Sequence Semantics):**
> To ensure absolute rigor for safety-critical systems, this interaction operates under strict SysML v2 mapping:
> - **Participants (Nodes):** Represent architectural **Parts** typed by **PartDefinitions**. The `API & Guardrail`, `Decision Router`, and `DR-AIS Log` constitute the Edge Node boundary.
> - **Solid Lines (`->>`):** Represent asynchronous **Signal** transmissions passing via **ItemFlows** between parts.
> - **Dashed Lines (`-->>`):** Represent **Return** messages resulting from a previous invocation or sequence.
> - **Self-Arrows (Step 2, Step 6):** Represent internal **Behaviors** evaluating a **Constraint** against an **Attribute Usage** (the SysML v2 concept for quantifiable part characteristics, e.g. RPM) to determine if structural hardware limits are breached.
> - **`alt` Blocks:** Represent **Alternative Successions** — conditional `if`/`else` branching within SysML v2 Interactions. Each `alt` block is divided into exactly **two visual operand regions** by a dashed horizontal divider:
>   - **Top region** → executes when the first guard (shown in the header) evaluates to **True**
>   - **Bottom region** → executes when the first guard evaluates to **False** (the `else` fallthrough)
>   - Only **one** region will ever execute per occurrence. The other is completely bypassed.
> - **`Note` Annotations:** Contextual inline explanations within each operand region, clarifying which guard fired and what the architectural consequence is.
> - **`[Guards]`:** Boolean expressions evaluated at decision points. Guards are shown in the header of each `alt` region in square brackets (e.g. `[if RPM > 6000]`). If the guard evaluates to False, all steps within that region are skipped and execution falls through to the `else` operand.
> - **Numbers (`1, 2, 3...`):** Denote the exact, deterministic chronological **Sequence** of execution.

## SysML v2 to Pydantic Guardrail Mapping

> [!IMPORTANT]
> **The Zero-Drift Principle:** Structural constraints defined in Model-Based Systems Engineering (MBSE) tools via SysML v2 are directly and automatically compiled into runtime Pydantic models. This guarantees absolute zero-requirement drift between the physics model and the executing code.

**Architecture Mapping Flow:**
```mermaid
graph TD
    A[SysML v2 Property Block] -->|Continuous Export| B(AST / JSON Schema definition)
    B -->|Code Generator Pipeline| C{Pydantic Model Factory}
    C -->|Output| D[Edge Guardrail Models]
    
    subgraph Compiled Artifact Example
    D1[class MomentumWheelState BaseMod:]
    D2[max_rpm: int = Field le=6000]
    D1 --- D2
    end
    D --> D1
```
**Mechanism:** 
If systems engineering parameters change (e.g., maximum momentum wheel limit from `6000` to `5500` RPM), the CI/CD pipeline immediately regenerates the edge Pydantic guardrail. The LLM is mathematically incapable of issuing a command outside this deterministic bound that reaches the hardware.

## Interface Definitions
- **Synthetic ACS ↔ Jetson Edge:** High-frequency UDP or Local REST. Sending JSON payloads containing Gyro (X,Y,Z), Momentum Wheel RPMs, and Euler angles.
- **Jetson Edge ↔ Claude API:** Secure HTTPS REST using structured Anthropic Tool Schemas (JSON) bounding LLM outputs.
- **Jetson Edge ↔ Eval Pipeline:** Log streaming of all prompt/response pairs with edge validation timestamps to calculate cognitive latency and RoCS.

## Compliance Framework Mapping
| SafeACS Element           | Target Standard           | Justification / Traceability                                                       |
| :------------------------ | :------------------------ | :--------------------------------------------------------------------------------- |
| Determinsitic Guardrails  | DO-178C, FAA OPA          | Ensures Intent, Correctness, and Innocuity regardless of heuristic LLM variations. |
| Audit Logging (DR-AIS)    | IEEE 7000 / ISO 42001     | Provides transparency, accountability, and system management traceability.         |
| Boundary Testing & Evals  | NIST AI RMF 1.0 (Measure) | Quantifies anomaly detection success against a bounded fatal deviation rate.       |
| Bimodal Decision Protocol | MIL-STD-882               | Limits LLM autonomy on critical pathways based on quantitative hazard severities.  |
