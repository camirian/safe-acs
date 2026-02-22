# HAZARDS.md (Risk Register & Hazard Analysis)

> [!CAUTION]
> **MIL-STD-882 System Safety Directive:**
> The following table defines the core Catastrophic and Critical hazards introduced by bounding probabilistic AI heuristics within a cyber-physical control loop. By design, no LLM output is trusted; the "Deterministic Edge Mitigation" explicitly acts as the final arbiter before any electrical pulse reaches the 3-axis Satellite Attitude Control System hardware. Residual risk must remain strictly at **Low**.

| Hazard ID | Hazard Description                                                                                         | Severity     | Likelihood | Deterministic Edge Mitigation                                                                             | Residual Risk |
| :-------- | :--------------------------------------------------------------------------------------------------------- | :----------- | :--------- | :-------------------------------------------------------------------------------------------------------- | :------------ |
| HZ-001    | LLM commands momentum wheel RPM above structural limits (6000 RPM) causing physical disintegration.        | Catastrophic | Occasional | Pydantic constraint `<Field(le=6000)>`. Drop command immediately, default to safe state.                  | Low           |
| HZ-002    | Cloud API inference latency (>3000ms) causes ACS to miss critical stabilization window.                    | Critical     | Probable   | Edge watchdog timeout (p95 < 50ms) severs API request and triggers deterministic PID fallback.            | Low           |
| HZ-003    | Unintended irreversible hardware actuation (Type 1) triggered by autonomous LLM loop.                      | Catastrophic | Remote     | Hard-coded authorization barrier requiring independent human-in-the-loop cryptographic approval.          | Low           |
| HZ-004    | Drift in system requirements leads to mismatch between physical hardware behavior and software guardrails. | Critical     | Occasional | MBSE SysML v2 automatic compilation pipeline ensures 1:1 trace parity between requirements and code.      | Low           |
| HZ-005    | Prompt injection or corrupted telemetry forces deterministic guardrail evasion.                            | Catastrophic | Remote     | Strict telemetry schema ingestion filtering; system halts and flags human UI if input schema is violated. | Low           |
