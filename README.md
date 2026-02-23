# Cyber-Physical AI Assurance Framework (SafeACS)

**Bounding Probabilistic Frontier AI inside Mission-Critical Cyber-Physical Systems**

> 📖 **New here?** Start with the **[WALKTHROUGH.md](./WALKTHROUGH.md)** — it explains the story, what each file does, and how to run the demo.

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

## 🧠 Architectural Philosophy: Bounding the Probabilistic

Frontier LLMs operate as probabilistic heuristic engines; they excel at generalizing across vast state spaces to detect anomalies that traditional PID loops or static edge limits miss. However, they lack mathematical guarantees of correctness. 

SafeACS reverses the standard AI paradigm: **We do not trust the LLM.**

Instead, the framework establishes a bimodal execution topology:
1. **The Core Physics (The Bound):** Deterministic Pydantic guardrails, automatically compiled from SysML v2 property blocks, run locally on an edge node. These act as the immutable laws of physics for the system—they mathematically guarantee the hardware (e.g., a Momentum Reaction Wheel) will never exceed its structural tolerance bounds, regardless of the prompt output.
2. **The Cognitive Layer (The Heuristic):** Anthropic's Steerable AI operates *inside* this deterministic bound, acting as a high-level cognitive observer. It flags anomalies and proposes optimizations, which are then ruthlessly filtered by the edge guardrail before actuation.

This separation of concerns mathematically guarantees system safety while maximizing cognitive ROI.

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
