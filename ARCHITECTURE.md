# ARCHITECTURE.md

## Executive Summary
The Cyber-Physical AI Assurance Framework (SafeACS) integrates Anthropic's steerable AI models (Claude) with mission-critical cyber-physical systems via an NVIDIA Jetson Orin Nano edge-compute node. Designed to operate within zero-requirements-drift aerospace constraints, SafeACS enforces deterministic safety boundaries using auto-generated Pydantic guardrails derived directly from SysML v2 property blocks. This architecture ensures all heuristic anomalies detected by Claude are verified against hard structural limits in under 50ms at the edge, maintaining absolute safety, bidirectionally traceable compliance, and auditable proof of innocence before any control action reaches the Satellite Attitude Control System.

## C4 Model Diagrams

### Context Level
```mermaid
C4Context
    title System Context diagram for SafeACS

    Person(operator, "Flight Operator / Verifier", "Monitors and approves Type 1 irreversible interventions.")
    System(safeacs, "SafeACS AI Assurance Framework", "Filters, analyzes, and guards ACS telemetry via LLM heuristics and deterministic edge rules.")
    System_Ext(satellite_acs, "Satellite ACS (Sim)", "Generates synthetic 3-axis stabilization & gyro telemetry.")
    System_Ext(claude_api, "Claude API", "Performs heuristic anomaly detection & cognitive analytics.")

    Rel(satellite_acs, safeacs, "Sends telemetry streams")
    Rel(safeacs, satellite_acs, "Sends verified control adjustments")
    Rel(safeacs, claude_api, "Requests heuristic analysis")
    Rel(claude_api, safeacs, "Returns anomaly detection results")
    Rel(operator, safeacs, "Approves/Rejects Type 1 Actions")
```

### Container Level
```mermaid
C4Container
    title Container diagram for SafeACS Edge Node

    System_Boundary(jetson_orin, "NVIDIA Jetson Orin Nano (Edge Node)") {
        Container(telemetry_gateway, "API Gateway / Receiver", "Python", "Ingests 100Hz ACS telemetry.")
        Container(guardrail_layer, "Deterministic Guardrails", "Pydantic / Python", "Executes strict constraint checks. Derived from SysML v2.")
        Container(decision_router, "Decision Protocol Router", "Python", "Routes Type 1 and Type 2 actions.")
        Container(audit_logger, "DR-AIS Logging Engine", "Python", "Immutable blast-radius & telemetry log.")
    }

    Container_Ext(claude_api, "Claude API (Cloud)", "Anthropic REST", "Heuristic inference engine.")
    Container_Ext(sim_engine, "Synthetic ACS", "Python", "Generates satellite state and accepts corrections.")
    Container_Ext(ui, "Streamlit Dashboard", "Python", "Human-in-the-loop validation UI.")

    Rel(sim_engine, telemetry_gateway, "Raw State (JSON)")
    Rel(telemetry_gateway, guardrail_layer, "Parsed Telemetry")
    Rel(guardrail_layer, decision_router, "Validated State")
    Rel(decision_router, claude_api, "Context Prompt (if valid)")
    Rel(claude_api, decision_router, "Proposed Action")
    Rel(decision_router, guardrail_layer, "Action Verification")
    Rel(guardrail_layer, sim_engine, "Authorized Command (Type 2)")
    Rel(decision_router, ui, "Requires Approval (Type 1)")
    Rel(decision_router, audit_logger, "Records State & Decision")
```

## SysML v2 to Pydantic Guardrail Mapping
**Concept:**
Structural constraints defined in Model-Based Systems Engineering (MBSE) tools via SysML v2 are directly compiled into runtime Pydantic models. This guarantees zero requirement drift.

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
