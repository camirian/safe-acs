# Citadel Proofing Tasks — `safe-acs`

> **Sprint 2** — These deliverables close 5 resume gap claims by expanding the scope of this repo.

## Deliverables

### 1. Digital Twin Feedback Loop (Claim: AI_NG_04)
**Goal:** Prove Digital Twin / DDRM architecture by closing the loop between MBSE models and simulation.

- [ ] Create a SysML v2 behavior model defining ACS state transitions
- [ ] Connect it to `acs_simulator.py` so model parameters drive simulation
- [ ] Feed simulator telemetry back to the Streamlit dashboard in real-time
- [ ] Document the closed-loop architecture in `ARCHITECTURE.md`

### 2. `/mission_engineering` UAF Views (Claim: EDU_JHU_04)
**Goal:** Prove Mission Engineering & Digital Thread proficiency.

- [ ] Create `mission_engineering/` directory
- [ ] Define an OV-1 (High-Level Operational Concept) for the SafeACS mission
- [ ] Define an OV-5b (Operational Activity Model) showing activity flows
- [ ] Reference UAF/DoDAF standards and link to the system's RTM

### 3. `CDR_RETROSPECTIVE.md` (Claim: CPS_NG_03)
**Goal:** Prove CDR leadership and systems decomposition methodology.

- [ ] Create `CDR_RETROSPECTIVE.md` at repo root
- [ ] Document a simulated CDR process: stakeholder needs → system functions → component allocation
- [ ] Include a decomposition tree (SysML Package Diagram style)
- [ ] Reference engineering review best practices (NASA/DoD standards)

### 4. `HARDWARE_SPEC.md` (Claim: CPS_NG_04)
**Goal:** Prove hardware subsystem ownership and environmental engineering knowledge.

- [ ] Create `HARDWARE_SPEC.md` at repo root
- [ ] Specify the Jetson Orin Nano edge deployment: thermal, vibration, EMI/EMC constraints
- [ ] Reference MIL-STD-810 environmental categories
- [ ] Include an interface control document (ICD) table for the edge node

### 5. `/notebooks/telemetry_signal_analysis.ipynb` (Claim: EDU_CSULA_03)
**Goal:** Prove signal processing & systems analysis on real telemetry data.

- [ ] Create `notebooks/` directory
- [ ] Implement FFT analysis on ACS simulator output signals
- [ ] Design and apply FIR/IIR filters to isolate frequency components
- [ ] Visualize signal-to-noise ratio and spectral density
- [ ] Include narrative linking EE 332 Systems Analysis concepts to the implementation
