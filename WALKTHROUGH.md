# SafeACS — Project Walkthrough

> **How to read, navigate, and run every part of this project.**  
> Start here if you are visiting for the first time.

---

## The Story in One Sentence

> We mathematically bounded a probabilistic frontier LLM (Anthropic Claude) inside a safety-critical satellite Attitude Control System — enforcing hard physical limits via SysML v2-derived Pydantic guardrails running locally on an NVIDIA Jetson Orin Nano edge node — so the LLM **cannot** directly harm the hardware, regardless of what it outputs.

This is not a tutorial. This is a reference architecture for building AI systems that comply with aerospace and defense safety standards.

---

## Recommended Reading Order

| Step | File                                                             | Purpose                                                                                 |
| ---- | ---------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| 1    | [`README.md`](./README.md)                                       | Start here. Architectural philosophy: "We do not trust the LLM."                        |
| 2    | [`ARCHITECTURE.md`](./ARCHITECTURE.md)                           | The full system design: C4 diagrams, SysML v2 Sequence Diagram, Zero-Drift Principle    |
| 3    | [`HAZARDS.md`](./HAZARDS.md)                                     | MIL-STD-882 hazard register: every identified risk and its deterministic mitigation     |
| 4    | [`RTM.md`](./RTM.md)                                             | DO-178C Traceability Matrix: every requirement linked to code and a verification method |
| 5    | [`TASKS.md`](./TASKS.md)                                         | Project roadmap across Phases 1–6                                                       |
| 6    | [`sim_engine/acs_simulator.py`](./sim_engine/acs_simulator.py)   | The satellite being protected: 3-axis stabilized ACS simulator                          |
| 7    | [`edge_node/guardrails.py`](./edge_node/guardrails.py)           | The deterministic law: SysML v2 → Pydantic constraints                                  |
| 8    | [`edge_node/claude_client.py`](./edge_node/claude_client.py)     | Claude's strictly bounded role as a heuristic observer                                  |
| 9    | [`edge_node/decision_router.py`](./edge_node/decision_router.py) | The bimodal protocol as running code                                                    |
| 10   | [`verify_phase3.py`](./verify_phase3.py)                         | 7/7 automated verification tests — run this first                                       |

---

## Repository Structure

```
safe-acs/
├── README.md               ← Philosophy and stack overview
├── ARCHITECTURE.md         ← System design (READ THIS)
├── HAZARDS.md              ← MIL-STD-882 hazard analysis
├── RTM.md                  ← DO-178C traceability matrix
├── TASKS.md                ← Project roadmap
├── AUDIT.md                ← DR-AIS immutable log specification
│
├── sim_engine/
│   └── acs_simulator.py   ← Phase 2: Synthetic ACS telemetry source
│
├── edge_node/              ← Phase 3: The guardrail stack
│   ├── guardrails.py      ← SysML v2 → Pydantic constraint engine
│   ├── claude_client.py   ← Anthropic API client (tool_use enforced)
│   └── decision_router.py ← Bimodal decision protocol orchestrator
│
└── verify_phase3.py        ← Run this to verify everything works
```

---

## Running the Demo

### Option A — Deterministic guardrails only (no API key required)

```bash
git clone https://github.com/camirian/safe-acs.git
cd safe-acs
pip install pydantic anthropic

python verify_phase3.py
```

**Expected output:**
```
[PASS] Guardrail: Nominal telemetry passes       | violations=0
[PASS] Guardrail: Fatal RPM violation detected   | severity=CATASTROPHIC
[PASS] Guardrail: Angular rate violation detected| violations=1
[PASS] Guardrail: Quaternion norm violation detected
[PASS] Router: Nominal returns GUARDRAIL_PASS_LLM_SKIPPED
[PASS] Router: Fatal RPM returns GUARDRAIL_VIOLATION_FATAL | requires_human=True
[PASS] LLMAnalysis: Pydantic schema validates correctly

=====================================
PHASE 3 VERIFICATION: 7/7 TESTS PASSED
=====================================
```

This confirms: when Wheel 2 hits 7,500 RPM (structural limit: 6,000), the guardrail catches it immediately, classifies it `CATASTROPHIC`, requires human approval, and **never invokes the LLM**. That is the architectural guarantee.

---

### Option B — Full end-to-end with Claude (requires `ANTHROPIC_API_KEY`)

```bash
export ANTHROPIC_API_KEY=your_key_here

python -c "
from sim_engine.acs_simulator import ACSSimulator
from edge_node.decision_router import DecisionRouter
import time

sim = ACSSimulator(frequency_hz=10.0)
router = DecisionRouter(llm_window_size=10, enable_llm=True)

# Phase A: Nominal telemetry (10 frames)
print('=== NOMINAL STATE (no LLM dispatch yet) ===')
for _ in range(10):
    event = router.process(sim.run_step())
    print(f'  [{event.outcome.value}]')
    time.sleep(sim.dt)

# Phase B: Inject a drift anomaly on Wheel 2 (50 RPM/sec drift)
print('\n=== DRIFT ANOMALY INJECTED ON WHEEL 2 ===')
sim.inject_anomaly(wheel_index=2, drift_rate_rpm=50.0)
for _ in range(10):
    event = router.process(sim.run_step())
    if event.llm_analysis:
        print(f'  anomaly={event.llm_analysis.anomaly_detected} '
              f'confidence={event.llm_analysis.confidence:.2f} '
              f'action={event.llm_analysis.recommended_action} '
              f'subsystem={event.llm_analysis.affected_subsystem}')
    time.sleep(sim.dt)
"
```

This demonstrates the full bimodal execution cycle: nominal frames accumulate silently through the guardrail, then when the window is dispatched to Claude, the LLM surfaces the monotonic RPM drift as an anomaly — with a confidence score and a proposed action that is still subject to a second guardrail pass before any actuation.

---

## What Each Phase Built

### Phase 1 — Architecture Definition

**Files:** `README.md`, `ARCHITECTURE.md`, `HAZARDS.md`, `RTM.md`, `TASKS.md`, `AUDIT.md`

Defined the full system architecture with institutional rigor before writing implementation code. The architectural centerpiece is the **SysML v2 Sequence Diagram** in `ARCHITECTURE.md`, which maps every diagram element to a formal modeling construct:

- **Participants** → `Parts` typed by `PartDefinitions`
- **Solid arrows** → `Signal` transmissions via `ItemFlows`
- **Dashed arrows** → `Return` messages
- **Self-arrows** → internal `Behaviors` evaluating `Constraints` against `Attribute Usages`
- **`alt` blocks** → `Alternative Successions` (conditional `if`/`else` branching)
- **`[Guards]`** → Boolean expressions; the top operand fires when `True`, the bottom when `False`

---

### Phase 2 — Synthetic ACS Simulator

**File:** `sim_engine/acs_simulator.py`

A physics-faithful 3-axis satellite ACS simulator. Outputs high-frequency JSON telemetry representing:
- **Unit quaternion attitude** propagated via Euler integration
- **3-axis angular rates** with Gaussian sensor noise
- **3x Reaction Wheel RPMs** (nominal ~2000 RPM)

Key method: `inject_anomaly(wheel_index, drift_rate_rpm)` — induces controlled, gradual RPM drift on any single wheel. This is what triggers the LLM's anomaly detection in the live demo.

---

### Phase 3 — Edge Node: Guardrails + Claude Integration

**Files:** `edge_node/guardrails.py`, `edge_node/claude_client.py`, `edge_node/decision_router.py`

The bimodal decision protocol from the sequence diagram, implemented as production-grade Python.

#### `guardrails.py` — The Deterministic Law

Each `Field()` constraint is a 1:1 trace to a SysML v2 `AttributeUsage`:

```python
class MomentumWheelStateGuardrail(BaseModel):
    rpm: float = Field(..., ge=-6000.0, le=6000.0)
    # ↑ SysML v2 AttributeUsage: ReactionWheelAssembly::max_rpm
    # ↑ MIL-STD-882 HZ-001 Mitigation: structural disintegration above ±6000 RPM
```

Three constraint classes:
- `MomentumWheelStateGuardrail` → HZ-001 (±6000 RPM)
- `AngularRateGuardrail` → HZ-002 (±5 deg/s per axis)
- `QuaternionNormGuardrail` → HZ-005 (|q| ≈ 1.0 ± 0.01)

#### `claude_client.py` — Claude's Bounded Role

Claude's compliance is **architectural, not prompt-based**:

```python
response = self.client.messages.create(
    ...
    tool_choice={"type": "any"},  # Claude MUST call the tool. No exceptions.
)
```

If Claude fails to call `report_anomaly_analysis`, a `RuntimeError` is raised and the decision router routes the situation to a human operator. Claude is not trusted to be cooperative.

#### `decision_router.py` — The Bimodal Orchestrator

Seven possible outcomes per telemetry tick, each emitting a structured `DecisionEvent` for the audit log:

| Outcome                            | What Happened                                                  |
| ---------------------------------- | -------------------------------------------------------------- |
| `GUARDRAIL_VIOLATION_FATAL`        | Structural limit breached. LLM bypassed. Safe-mode PID active. |
| `GUARDRAIL_VIOLATION_CRITICAL`     | Limit breached. LLM bypassed. Human alerted.                   |
| `GUARDRAIL_PASS_LLM_SKIPPED`       | Nominal. Accumulating telemetry window.                        |
| `GUARDRAIL_PASS_LLM_NOMINAL`       | Nominal. Claude confirmed no anomaly.                          |
| `GUARDRAIL_PASS_LLM_ANOMALY_TYPE2` | Anomaly detected. Reversible — autonomous actuation.           |
| `GUARDRAIL_PASS_LLM_ANOMALY_TYPE1` | Anomaly detected. Irreversible — human approval required.      |
| `LLM_TRUST_BOUNDARY_VIOLATION`     | Claude violated the protocol. Routed to human review.          |

---

## Standards Compliance Evidence

| Standard            | Where Applied                        | Evidence                                                                           |
| ------------------- | ------------------------------------ | ---------------------------------------------------------------------------------- |
| **SysML v2**        | Architecture modeling language       | `ARCHITECTURE.md` — all diagram elements annotated with formal SysML v2 constructs |
| **MIL-STD-882**     | Hazard severity/probability taxonomy | `HAZARDS.md` — HZ-001 through HZ-005 with mitigations                              |
| **DO-178C**         | Requirements traceability            | `RTM.md` — stakeholder → derived → verification method                             |
| **NIST AI RMF 1.0** | AI risk governance                   | `README.md` — trust boundaries and blast-radius auditing                           |
| **FAA OPA**         | Overarching Properties for AI        | `HAZARDS.md` — LLM trust boundary constraints                                      |

---

## What Comes Next

| Phase       | Goal                                                                     |
| ----------- | ------------------------------------------------------------------------ |
| **Phase 4** | DR-AIS Immutable Logging Router + Statistical Evaluation Harness         |
| **Phase 5** | Streamlit human-in-the-loop dashboard — Type 1 cryptographic approval UI |
| **Phase 6** | Open-source packaging and enterprise demo formatting                     |
