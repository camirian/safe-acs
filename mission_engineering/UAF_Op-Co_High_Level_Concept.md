# UAF Op-Co: High-Level Operational Concept

**Former DoDAF Equivalent:** OV-1 (High-Level Operational Concept Graphic)  
**UAF Domain:** Operational  
**UAF Model Kind:** Concept (Op-Co)

## Mission Context
The Operation Concept (Op-Co) graphic defines the macro-level mission scenario. It illustrates the primary operational nodes, their environments, and the critical systems engineering challenge SafeACS solves: bridging the gap between an untrusted probabilistic Cloud LLM and vulnerable Space Vehicle (SV) hardware.

In accordance with the **DoD Mission Engineering Guide (MEG)**, the system of interest is the *End-to-End Mission Capability*—not merely the ACS software. The mission fails if adversarial LLM hallucination or supply chain poisoning results in a kinetic hardware loss. SafeACS serves as the structural mission assurance boundary.

---

## Operational Architecture

```mermaid
flowchart TB
    %% Definitions
    classDef space fill:#0b1e36,color:#fff,stroke:#4a90e2,stroke-width:2px;
    classDef ground fill:#1f2937,color:#fff,stroke:#10b981,stroke-width:2px;
    classDef threat fill:#450a0a,color:#fff,stroke:#ef4444,stroke-width:2px;
    classDef boundary fill:none,stroke:#f59e0b,stroke-width:3px,stroke-dasharray: 5 5;

    %% Mission Nodes
    subgraph Space_Domain [Space Segment: Vulnerable Hardware]
        direction LR
        ACS[Satellite Attitude Control System<br/>Reaction Wheels & Gyros]:::space
    end

    subgraph Assurance_Boundary [Mission Assurance Boundary: SafeACS]
        direction TB
        Jetson[Edge Node: Jetson Orin Nano<br/>Deterministic Pydantic Guardrails]:::space
    end

    subgraph Cloud_Domain [Cloud Segment: Probabilistic Intelligence]
        direction TB
        Claude[Anthropic Claude API<br/>Heuristic Anomaly Detection]:::threat
        note_threat>Threat Vector: LLM Hallucination / Poisoning]:::threat
    end

    subgraph Ground_Domain [Ground Segment: Human-in-the-Loop]
        direction LR
        Operator((Space Force / Flight Operator<br/>Cryptographic Authority)):::ground
        Dashboard[Mission Control Dashboard<br/>React + FastAPI]:::ground
    end

    %% Operational Exchanges
    ACS -->|Continuous Telemetry<br/>[High-Frequency JSON]| Jetson
    Jetson -->|Zero-Drift Verified Commands<br/>[Actuation]| ACS
    
    Jetson <-->|Tool Use API Calls<br/>[Heuristic Context]| Claude
    Claude -.- note_threat
    
    Jetson -->|Irreversible Action Proposed<br/>[Type 1 Mitigation]| Dashboard
    Dashboard -->|Cryptographic Approval<br/>[Human Override]| Jetson
    Operator <-->|Monitors & Approves| Dashboard

    %% Styling
    class Assurance_Boundary boundary
```

## Concept of Operations (CONOPS)

1.  **Continuous Ingestion:** The Satellite (Space Segment) emits high-frequency telemetry.
2.  **The Choke Point:** The SafeACS Edge Node intercepts all telemetry and command traffic. This node enforces hard mathematical constraints derived directly from SysML v2 models.
3.  **Probabilistic Offload:** SafeACS queries the Claude LLM (Cloud Segment) to detect subtle, heuristic anomalies that evade traditional PID thresholds.
4.  **Bimodal Authority:** If the LLM proposes an irreversible action (e.g., shutting down a reaction wheel), SafeACS inherently distrusts the LLM. It halts the action at the Mission Assurance Boundary and routes a request to the Flight Operator (Ground Segment) for cryptographic human-in-the-loop approval.
