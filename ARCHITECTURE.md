# ARCHITECTURE.md

## Executive Summary
The Cyber-Physical AI Assurance Framework (SafeACS) integrates Anthropic's steerable AI models (Claude) with mission-critical cyber-physical systems via an NVIDIA Jetson Orin Nano edge-compute node. Designed to operate within zero-requirements-drift aerospace constraints, SafeACS enforces deterministic safety boundaries using auto-generated Pydantic guardrails derived directly from SysML v2 property blocks. This architecture ensures all heuristic anomalies detected by Claude are verified against hard structural limits in under 50ms at the edge, maintaining absolute safety, bidirectionally traceable compliance, and auditable proof of innocence before any control action reaches the Satellite Attitude Control System.

## C4 Model Diagrams

### Context Level
```mermaid
flowchart TD
    subgraph External
        operator(("Flight Operator / Verifier\n[Person]"))
        satellite_acs["Satellite ACS (Sim)\n[Software System]"]
        claude_api["Claude API\n[Software System]"]
    end
    
    safeacs("SafeACS AI Assurance Framework\n[Software System]")

    satellite_acs -- "Sends telemetry streams" --> safeacs
    safeacs -- "Sends verified control adjustments" --> satellite_acs
    safeacs -- "Requests heuristic analysis" --> claude_api
    claude_api -- "Returns anomaly detection results" --> safeacs
    operator -- "Approves/Rejects Type 1 Actions" --> safeacs
    
    classDef person fill:#08427b,color:#fff,stroke:#052e56
    classDef system fill:#1168bd,color:#fff,stroke:#0b4884
    classDef ext_system fill:#999999,color:#fff,stroke:#8a8a8a
    
    class operator person
    class safeacs system
    class satellite_acs,claude_api ext_system
```

### Container Level
```mermaid
flowchart TD
    subgraph jetson_orin [NVIDIA Jetson Orin Nano / Edge Node]
        telemetry_gateway("API Gateway / Receiver\n[Container: Python]")
        guardrail_layer("Deterministic Guardrails\n[Container: Pydantic / Python]")
        decision_router("Decision Protocol Router\n[Container: Python]")
        audit_logger("DR-AIS Logging Engine\n[Container: Python]")
    end

    claude_api["Claude API (Cloud)\n[External System]"]
    sim_engine["Synthetic ACS\n[External System]"]
    ui["Streamlit Dashboard\n[External System]"]

    sim_engine -- "Raw State (JSON)" --> telemetry_gateway
    telemetry_gateway -- "Parsed Telemetry" --> guardrail_layer
    guardrail_layer -- "Validated State" --> decision_router
    decision_router -- "Context Prompt (if valid)" --> claude_api
    claude_api -- "Proposed Action" --> decision_router
    decision_router -- "Action Verification" --> guardrail_layer
    guardrail_layer -- "Authorized Command (Type 2)" --> sim_engine
    decision_router -- "Requires Approval (Type 1)" --> ui
    decision_router -- "Records State & Decision" --> audit_logger

    classDef container fill:#438dd5,color:#fff,stroke:#3c7fc0
    classDef ext_system fill:#999999,color:#fff,stroke:#8a8a8a
    classDef boundary fill:none,stroke:#444,stroke-width:2px,stroke-dasharray: 5 5
    
    class telemetry_gateway,guardrail_layer,decision_router,audit_logger container
    class claude_api,sim_engine,ui ext_system
    class jetson_orin boundary
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
