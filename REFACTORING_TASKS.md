# Refactoring & Engineering Tasks — `safe-acs`

> **Sprint 2** — These deliverables close 5 resume gap claims by expanding the scope of this repo.

## Deliverables

### 1. Digital Twin Feedback Loop (Claim: AI_NG_04)
**Goal:** Prove Digital Twin / DDRM architecture by closing the loop between MBSE models and simulation.

- [x] Create a SysML v2 behavior model defining ACS state transitions
- [x] Connect it to `acs_simulator.py` so model parameters drive simulation
- [x] Feed simulator telemetry back to the Streamlit dashboard in real-time
- [x] Document the closed-loop architecture in `ARCHITECTURE.md`

### 2. `/mission_engineering` UAF Views (Claim: EDU_JHU_04)
**Goal:** Prove Mission Engineering & Digital Thread proficiency.

- [x] Create `mission_engineering/` directory
- [x] Define an OV-1 (High-Level Operational Concept) for the SafeACS mission
- [x] Define an OV-5b (Operational Activity Model) showing activity flows
- [x] Reference UAF/DoDAF standards and link to the system's RTM

### 3. `CDR_RETROSPECTIVE.md` (Claim: CPS_NG_03)
**Goal:** Prove CDR leadership and systems decomposition methodology.

- [x] Create `CDR_RETROSPECTIVE.md` at repo root
- [x] Document a simulated CDR process: stakeholder needs → system functions → component allocation
- [x] Include a decomposition tree (SysML Package Diagram style)
- [x] Reference engineering review best practices (NASA/DoD standards)

### 4. `HARDWARE_SPEC.md` (Claim: CPS_NG_04)
**Goal:** Prove hardware subsystem ownership and environmental engineering knowledge.

- [x] Create `HARDWARE_SPEC.md` at repo root
- [x] Specify the Jetson Orin Nano edge deployment: thermal, vibration, EMI/EMC constraints
- [x] Reference MIL-STD-810 environmental categories
- [x] Include an interface control document (ICD) table for the edge node

### 5. `/notebooks/telemetry_signal_analysis.ipynb` (Claim: EDU_CSULA_03)
**Goal:** Prove signal processing & systems analysis on real telemetry data.

- [x] Create `notebooks/` directory
- [x] Implement FFT analysis on ACS simulator output signals
- [x] Design and apply FIR/IIR filters to isolate frequency components
- [x] Visualize signal-to-noise ratio and spectral density
- [x] Include narrative linking EE 332 Systems Analysis concepts to the implementation

---

> **Sprint 3** — These deliverables prove end-to-end cloud-native and edge deployment capabilities.

### 6. Edge-Optimized Containerization (Claim: CLOUD_NG_01)
**Goal:** Prove containerization expertise specifically for constrained edge architectures.

- [x] Create an edge-optimized `Dockerfile.edge` targeting `linux/arm64` (Jetson Orin Nano).
- [x] Minimize image footprint for restricted SWaP environments using a multi-stage build.
- [x] Document the cross-compilation strategy.

### 7. Kubernetes Edge Manifests (Claim: K8S_CSULA_01)
**Goal:** Prove container orchestration skills for edge computing environments.

- [x] Create a `k8s/` directory containing Kubernetes manifests.
- [x] Define Deployment and Service YAML configurations optimized for K3s / MicroK8s.
- [x] Include resource limits (CPU/Memory) aligned with our `HARDWARE_SPEC.md` constraints.
