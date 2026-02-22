# Cyber-Physical AI Assurance Framework (SafeACS)

**Bounding Probabilistic Frontier AI inside Mission-Critical Cyber-Physical Systems**

This repository contains the architecture, safety analysis, and synthetic simulation environment for SafeACS. It demonstrates how to integrate steerable frontier AI models (Anthropic Claude) within zero-requirements-drift aerospace constraints, enforcing deterministic safety boundaries via auto-generated Pydantic guardrails running on an NVIDIA Jetson Orin Nano edge node.

---

## ✅ Core Competencies & Demonstrations

Successfully architecting and simulating this framework demonstrates core competencies in:

- **Mission-Critical Systems Engineering:** Applying aerospace standards (DO-178C, FAA OPA, MIL-STD-882) to modern AI implementations.
- **MBSE-to-Code Traceability:** Designing pipelines that automatically compile SysML v2 property blocks directly into runtime execution code (Pydantic guardrails).
- **Edge AI & Determinism:** Executing strict, high-frequency structural constraint checks at the edge (Jetson Orin Nano) independent of cloud inference latency.
- **AI Safety & Assurance (DR-AIS):** Implementing immutable blast-radius audit logs, bimodal decision protocols, and return-on-cognitive-spend (RoCS) metrics based on NIST AI RMF 1.0 and IEEE 7000.
- **Cyber-Physical Simulation:** Developing high-fidelity synthetic telemetry generators (3-axis stabilized Satellite Attitude Control Systems) for component boundary testing.

---

## 🛠️ Software Stack & Key Tools

| Component                    | Version / Type          | Purpose                                                    |
| :--------------------------- | :---------------------- | :--------------------------------------------------------- |
| **Operating System**         | Ubuntu 22.04 LTS        | Standard deployment target for Jetson edge nodes           |
| **Logic & Simulation**       | Python 3.10+            | Core execution and synthetic ACS telemetry generation      |
| **Edge Compute**             | NVIDIA Jetson Orin Nano | Local execution of generic Python API Gateway & guardrails |
| **Deterministic Guardrails** | Pydantic                | Auto-derived structural constraints (compiled from SysML)  |
| **Heuristic Engine**         | Anthropic Claude API    | Cloud-based cognitive inference and anomaly detection      |
| **UI / Dashboard**           | Streamlit               | Human-in-the-loop verification and DR-AIS telemetry viewer |

---

## 📝 Architecture & Verification Details

The foundation of SafeACS is heavily documented, rigorously planned, and bidirectionally traceable. Please review the core engineering artifacts:

- [`ARCHITECTURE.md`](./ARCHITECTURE.md): Executive summary, C4 diagrams, and SysML-to-code mapping.
- [`HAZARDS.md`](./HAZARDS.md): Top 5 system hazards, severities, and deterministic mitigations.
- [`RTM.md`](./RTM.md): Requirements Traceability Matrix linking stakeholder limits to software verification.
- [`TASKS.md`](./TASKS.md): The multi-phase execution strategy for building the framework.
- [`AUDIT.md`](./AUDIT.md): Self-audit criteria for the project's zero-drift environment.
- [`sim_engine/acs_simulator.py`](./sim_engine/acs_simulator.py): The Python simulation for generating high-fidelity attitude control telemetry.

---

## 📜 License

This project is licensed under the Apache 2.0 License. See the [`LICENSE`](./LICENSE) file for details.
