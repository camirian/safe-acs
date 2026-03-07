# SafeACS: Cyber-Physical AI Assurance Framework

**Project Walkthrough: How to read, navigate, and demo the repository.**

### The Story in One Sentence

We mathematically bounded a probabilistic frontier LLM (Anthropic's Claude) inside a safety-critical satellite Attitude Control System (ACS), enforcing hard physical limits via SysML v2-derived Pydantic guardrails running locally on an edge node—guaranteeing the LLM can *never* directly harm the hardware, regardless of its output.

---

## 📁 Where to Look on GitHub

All work lives at: [github.com/camirian/safe-acs](https://github.com/camirian/safe-acs) (branch: `main`)

### Repository Structure at a Glance

```text
safe-acs/
├── README.md              ← Start here. Architecture philosophy.
├── ARCHITECTURE.md        ← SysML v2 diagrams and the Bimodal Decision Protocol.
├── HAZARDS.md             ← MIL-STD-882 hazard analysis.
├── RTM.md                 ← DO-178C Traceability Matrix.
├── TASKS.md               ← Project roadmap (Phases 1–6).
├── AUDIT.md               ← DR-AIS audit log specification.
│
├── sim_engine/
│   └── acs_simulator.py   ← Phase 2: Synthetic ACS telemetry source (The Kinetic-Twin).
│
└── edge_node/             ← Phase 3: The Deterministic Guardrail Stack.
    ├── guardrails.py      ← SysML → Pydantic constraint engine.
    ├── claude_client.py   ← Anthropic tool_use heuristic client.
    └── decision_router.py ← Bimodal protocol orchestrator.
```

---

## 🚀 The Demo

### Option A: Run the Deterministic Verification (Offline)

This 30-second test proves the constraint layer operates independently of the LLM. Claude is never invoked for a fatal hardware violation—the edge node acts immediately.

```bash
# Clone the repo and install dependencies
git clone https://github.com/camirian/safe-acs.git && cd safe-acs
pip install pydantic anthropic

# Run the Phase 3 verification (No API key needed)
python verify_phase3.py
```

**Expected Output:** A 7/7 test pass demonstrating the router catching simulated `CATASTROPHIC` RPM and Angular Rate violations before they can reach the LLM.

---

### Option B: Live End-to-End with Claude

This demonstrates the live **Bimodal Protocol**: nominal frames accumulate silently, but when a subtle drift anomaly is injected, Claude surfaces it with a confidence score and a recommended action.

```bash
export ANTHROPIC_API_KEY="your_api_key_here"
```

Save the following as `run_demo.py` and execute with `python run_demo.py`:

```python
from sim_engine.acs_simulator import ACSSimulator
from edge_node.decision_router import DecisionRouter
import time

sim = ACSSimulator(frequency_hz=10.0)
router = DecisionRouter(llm_window_size=10, enable_llm=True)

print('=== NOMINAL STATE ===')
for _ in range(10):
    event = router.process(sim.run_step())
    print(f'  [{event.outcome.value}]')
    time.sleep(sim.dt)

print('\n=== INJECTING DRIFT ANOMALY ===')
sim.inject_anomaly(wheel_index=2, drift_rate_rpm=50.0)
for _ in range(10):
    event = router.process(sim.run_step())
    if event.llm_analysis:
        print(f'  [LLM] anomaly={event.llm_analysis.anomaly_detected} | '
              f'confidence={event.llm_analysis.confidence:.2f} | '
              f'subsystem={event.llm_analysis.affected_subsystem}')
    time.sleep(sim.dt)
```

---

### Option C: The Human-in-the-Loop Web Dashboard

If you prefer a visual, interactive experience, you can run the enterprise Streamlit dashboard locally.

```bash
# Run the dashboard on localhost:8501
streamlit run ui/app.py
```

The dashboard allows you to:
- Inject structural FAULTs and heuristic DRIFTs via sidebar buttons.
- Watch live Pydantic guardrail interceptions.
- Review and cryptographically approve Claude's Type 1 mitigation requests.
- Read the DR-AIS JSONL audit ledger in real-time.

---

### Option D: Deploy to Google Cloud Run

To host the SafeACS Mission Control dashboard publicly for zero-friction demonstrations, use the included Dockerfile.

```bash
# 1. Authenticate with Google Cloud
gcloud auth login
gcloud config set project YOUR_PROJECT_ID

# 2. Deploy directly from source to Cloud Run
gcloud run deploy safe-acs-demo \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars ANTHROPIC_API_KEY="your_api_key_here" \
  --port 8080
```

---

## 🏗️ What Was Built Phase by Phase

### Phase 1 — Architecture Definition (The Iron Frame)

**Goal:** Define the problem with institutional rigor before writing a line of code.

The key design decision: The `ARCHITECTURE.md` sequence diagram is a strict SysML v2 Interaction model. Every element maps to a precise formal construct, ensuring zero-drift from requirements to code.

- **`HAZARDS.md`:** MIL-STD-882 hazard register (HZ-001 through HZ-005).
- **`RTM.md`:** DO-178C Requirements Traceability Matrix linking every stakeholder need to a verification method.

---

### Phase 2 — Synthetic ACS Simulator (The Kinetic-Twin)

**Goal:** Build a physics-faithful telemetry source to test the guardrail stack against.

- **`sim_engine/acs_simulator.py`:** Simulates a 3-axis stabilized satellite utilizing unit quaternion attitude propagation (Euler integration) and Gaussian sensor noise.
- **The Breakthrough:** The `inject_anomaly()` method induces controlled RPM micro-drift, creating the exact heuristic failure states the LLM is designed to catch—states that are structurally legal but operationally catastrophic if left undetected.

---

### Phase 3 — Edge Node: Deterministic Guardrails & Claude Integration

**Goal:** Implement the bimodal protocol as production-grade Python.

#### 1. The Constraint Engine (`guardrails.py`)

This is the compiled output of the SysML v2 MBSE pipeline. Each `Field()` is a direct 1:1 trace to a physical hardware attribute limit:

```python
class MomentumWheelStateGuardrail(BaseModel):
    rpm: float = Field(..., ge=-6000.0, le=6000.0)
    # ↑ This Field() IS the SysML v2 AttributeUsage constraint. One-to-one trace.
```

Three constraint classes, each tied to a MIL-STD-882 hazard:

| Guardrail                     | SysML Source            | Constraint           | HZ Ref |
| ----------------------------- | ----------------------- | -------------------- | ------ |
| `MomentumWheelStateGuardrail` | `ReactionWheelAssembly` | `±6000 RPM`          | HZ-001 |
| `AngularRateGuardrail`        | `Gyroscope`             | `±5 deg/s` per axis  | HZ-002 |
| `QuaternionNormGuardrail`     | `AttitudeSolution`      | `\|q\| ≈ 1.0 ± 0.01` | HZ-005 |

#### 2. The Trust Boundary (`claude_client.py`)

Claude's constraints are **architectural, not prompt-based**. By enforcing Anthropic's Tool Use API, Claude *cannot* return unstructured text:

```python
response = self.client.messages.create(
    ...
    tool_choice={"type": "any"},  # Claude MUST call the tool. Free text is forbidden.
)
```

If Claude fails to call `report_anomaly_analysis`, a `RuntimeError` routes the situation to a human operator. The system does not trust the LLM to be cooperative.

This is the direct implementation of Anthropic's core mission: a steerable, interpretable AI whose behavior is verifiably bounded—not by hope, but by architecture.

#### 3. The Bimodal Orchestrator (`decision_router.py`)

The router processes every telemetry tick and emits an immutable `DecisionEvent` for the audit log:

| Outcome                            | What Happened                                                           |
| ---------------------------------- | ----------------------------------------------------------------------- |
| `GUARDRAIL_VIOLATION_FATAL`        | Structural limit breached. LLM bypassed. Safe-mode PID active.          |
| `GUARDRAIL_VIOLATION_CRITICAL`     | Limit breached. LLM bypassed. Human alerted.                            |
| `GUARDRAIL_PASS_LLM_SKIPPED`       | Nominal. Accumulating telemetry window.                                 |
| `GUARDRAIL_PASS_LLM_NOMINAL`       | Nominal. Claude confirmed no anomaly.                                   |
| `GUARDRAIL_PASS_LLM_ANOMALY_TYPE2` | Anomaly detected. Reversible — autonomous actuation.                    |
| `GUARDRAIL_PASS_LLM_ANOMALY_TYPE1` | Anomaly detected. Irreversible — human cryptographic approval required. |
| `LLM_TRUST_BOUNDARY_VIOLATION`     | Claude broke the protocol. Routed to human review.                      |

---

## 🔍 Evidence of Rigor

| Evidence                         | Where to Find It                              |
| -------------------------------- | --------------------------------------------- |
| SysML v2 Terminology             | `ARCHITECTURE.md` (Interpretation block)      |
| MIL-STD-882 Hazard Register      | `HAZARDS.md`                                  |
| DO-178C Traceability Matrix      | `RTM.md`                                      |
| SysML → Pydantic 1:1 Trace       | `edge_node/guardrails.py` (Inline docstrings) |
| Anthropic `tool_use` Enforcement | `edge_node/claude_client.py`                  |
| Automated Verification Tests     | `verify_phase3.py` (7/7 Pass Rate)            |

---

### Sprint 2: Deliverable 1 - Digital Twin Feedback Loop

**Goal:** Implement a closed-loop Digital Twin architecture, mapping a declarative Model-Based Systems Engineering (MBSE) state machine directly to the runtime simulation and frontend UI.

#### 1. The SysML v2 Behavioral Model
Authored `models/acs_behavior.sysml`, defining the deterministic state boundaries for the Attitude Control System:
*   `Nominal`: Wheel RPM ≤ 3000
*   `Anomaly_Drift`: 3000 < Wheel RPM ≤ 6000
*   `Fatal_Fault`: Wheel RPM > 6000
*   `Safe_Mode`: Post-fault recovery state.

#### 2. Simulator Integration
Updated `sim_engine/acs_simulator.py` to evaluate these exact structural boundaries at 5Hz during the physics update loop. The simulator now maintains and emits a `sysml_state` variable within its JSON telemetry stream, eliminating any drift between the engineering model and the executing code.

#### 3. Full-Stack Data Thread
Updated `backend/main.py` to forward this `sysml_state` to the React frontend. In `frontend/src/App.tsx`, the main "SYS STATUS" badge and its pulse color are now strictly bound to this SysML state, providing an unbroken data thread from the systems model to the operator's dashboard.

---

## ⏭️ What Comes Next

- **Sprint 2: Deliverable 2:** `/mission_engineering` UAF Views (Claim: EDU_JHU_04).
- **Sprint 2: Deliverable 3:** `CDR_RETROSPECTIVE.md` (Claim: CPS_NG_03).
