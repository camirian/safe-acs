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
flowchart TD
    classDef space fill:#0b1e36,color:#fff,stroke:#4a90e2,stroke-width:2px;
    classDef edge fill:#1f2937,color:#fff,stroke:#f59e0b,stroke-width:3px;
    classDef cloud fill:#450a0a,color:#fff,stroke:#ef4444,stroke-width:2px;
    classDef ground fill:#1f2937,color:#fff,stroke:#10b981,stroke-width:2px;
    classDef dec fill:#4a5568,color:#fff,stroke:#94a3b8,stroke-width:2px,shape:diamond;

    %% Swimlanes
    subgraph Space_Domain [Space Segment: Attitude Control System]
        A1(Emit Telemetry Packet:<br/>5Hz JSON):::space
        A6(Execute Approved Actuation):::space
        A7(Log Dropped Actuation):::space
        A8(Execute Hard Override):::space
    end

    subgraph Assurance_Boundary [Edge Segment: SafeACS Mission Boundary]
        B1(Ingest Telemetry):::edge
        B2{Evaluate SysML<br/>Guardrails}:::dec
        B3(Trigger Zero-Drift Override):::edge
        B4(Forward Context via Tool API):::edge
        B5{Determine Action<br/>Reversibility}:::dec
        B6(Approve Type 2:<br/>Autonomous Execution):::edge
        B7(Halt Type 1 Action:<br/>Request Approval):::edge
    end

    subgraph Cloud_Domain [Cloud Segment: Claude LLM]
        C1(Analyze Heuristic Context):::cloud
        C2(Propose Actuation<br/>via Tool Invoke):::cloud
    end

    subgraph Ground_Domain [Ground Segment: Flight Operator]
        D1{Cryptographic<br/>Review}:::dec
        D2(Sign Action):::ground
        D3(Deny Action):::ground
    end

    %% Activity Flow
    A1 -->|"Telemetry Stream"| B1
    B1 --> B2
    
    B2 -->|"Violation<br/>(e.g., RPM > 6000)"| B3
    B3 -->|"Type 0 Mitigation"| A8
    
    B2 -->|"Nominal Physics"| B4
    B4 -->|"API Request"| C1
    C1 --> C2
    C2 -->|"Tool Proposal"| B5
    
    B5 -->|"Reversible<br/>(e.g., Log/Ping)"| B6
    B6 --> A6
    
    B5 -->|"Irreversible<br/>(e.g., Halt Wheel)"| B7
    B7 -->|"UI Prompt"| D1
    
    D1 -->|"Approved"| D2
    D2 -->|"Signed Command"| A6
    
    D1 -->|"Rejected"| D3
    D3 -->|"Drop Command"| A7
```

## Traceability to Design Specifications

To satisfy the DoD Mission Engineering Guide (MEG) requirement for an unbroken "Digital Thread," the activities in this sequence map directly to our specific engineering artifacts:

1. **Phase 2 (Structural Verification)** directly mitigates **Hazard H-02 (Hardware Limit Exceedance)** as defined in [`HAZARDS.md`](../HAZARDS.md).
2. **Phase 4 (Bimodal Routing)** fulfills **Requirement REQ-SEC-01 (Type 1 Cryptographic Approval)** as defined in [`RTM.md`](../RTM.md).
3. The underlying physics constraints evaluated in Phase 2 are derived structurally from the MBSE properties in [`acs_behavior.sysml`](../models/acs_behavior.sysml).
