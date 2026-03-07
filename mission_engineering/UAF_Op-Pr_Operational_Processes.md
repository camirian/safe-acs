# UAF Op-Pr: Operational Processes

**Former DoDAF Equivalent:** OV-5b (Operational Activity Model)  
**UAF Domain:** Operational  
**UAF Model Kind:** Processes (Op-Pr)

## Process Context
The Operational Processes (Op-Pr) model describes the exact sequence of activities, behavioral flows, and data exchanges conducted to achieve the mission objective.

For **SafeACS**, this sequence maps the flow of a single telemetry packet from the physical hardware (Space Segment), through the Mission Assurance Boundary (Edge Segment), out to the probabilistic AI (Cloud Segment), and finally through the deterministic Bimodal Actuation Protocol.

---

## Operational Activity Flow (Bimodal Protocol)

```mermaid
sequenceDiagram
    autonumber
    
    %% Define Actors / Nodes
    participant Sat as Space Segment<br/>(Attitude Control System)
    participant Edge as Edge Segment<br/>(SafeACS Mission Boundary)
    participant Cloud as Cloud Segment<br/>(Claude LLM)
    participant Ground as Ground Segment<br/>(Flight Operator)

    %% Operational Sequence
    Note over Sat,Edge: Phase 1: High-Frequency Ingestion
    Sat->>Edge: Emit Telemetry Packet (5Hz JSON)
    
    Note over Edge: Phase 2: Structural Verification
    activate Edge
    Edge->>Edge: Evaluate against SysML v2 Guardrails
    
    alt Guardrail Violation (e.g., RPM > 6000)
        Edge-->>Sat: [Type 0] Hard Actuation Override (Zero-Drift)
    else Nominal Physics
        %% Passing nominal data to Claude
        Note over Edge,Cloud: Phase 3: Probabilistic Evaluation
        Edge->>Cloud: Forward telemetry context via Tool Use API
        activate Cloud
        Cloud-->>Edge: [Tool Invoke] Propose Actuation (Heuristic Anomaly)
        deactivate Cloud
        
        Note over Edge: Phase 4: Bimodal Routing
        alt Proposes Reversible Action
            Edge-->>Sat: [Type 2] Autonomous Execution (e.g., Log/Ping)
        else Proposes Irreversible Action
            Edge->>Ground: [Type 1] Action Halted. Request Human Approval
            activate Ground
            
            alt Ground Rejects
                Ground-->>Edge: Cryptographic Deny
                Edge--xSat: Actuation Dropped
            else Ground Approves
                Ground-->>Edge: Cryptographic Sign
                Edge-->>Sat: [Type 1] Execute Signed Actuation
            end
            deactivate Ground
        end
    end
    deactivate Edge
```

## Traceability to Design Specifications

To satisfy the DoD Mission Engineering Guide (MEG) requirement for an unbroken "Digital Thread," the activities in this sequence map directly to our specific engineering artifacts:

1. **Phase 2 (Structural Verification)** directly mitigates **Hazard H-02 (Hardware Limit Exceedance)** as defined in [`HAZARDS.md`](../HAZARDS.md).
2. **Phase 4 (Bimodal Routing)** fulfills **Requirement REQ-SEC-01 (Type 1 Cryptographic Approval)** as defined in [`RTM.md`](../RTM.md).
3. The underlying physics constraints evaluated in Phase 2 are derived structurally from the MBSE properties in [`acs_behavior.sysml`](../models/acs_behavior.sysml).
