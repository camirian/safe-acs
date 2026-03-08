# Critical Design Review (CDR) Retrospective: SafeACS Edge Architecture

**Project:** Cyber-Physical AI Assurance Framework (SafeACS)
**Phase:** CDR (Post-Execution Retrospective)
**Author:** Lead Systems Architect

## 1. Executive Summary
This document captures the primary architectural trade-offs, system decomposition decisions, and risk mitigation strategies finalized during the Critical Design Review (CDR) for the SafeACS edge-compute node. The primary objective of the CDR was to guarantee that the NVIDIA Jetson Orin Nano could safely enforce deterministic structural constraints while asynchronously brokering probabilistic heuristic queries to the Anthropic Claude API without violating the 50ms real-time control loop.

## 2. Key Architectural Decisions & Trade-offs

### 2.1 Bimodal Routing vs. Multimodal Monolith
*   **Original Concept:** Route all telemetry through a local small-parameter (e.g., Llama-3 8B) LLM to determine *both* structural bounding (guardrails) and anomaly detection.
*   **Trade-off Analysis:** While a multimodal monolith simplified the state machine, it failed the DO-178C requirement for mathematical determinism. LLMs are probabilistic heuristic engines; they cannot mathematically guarantee an output.
*   **CDR Decision:** We adopted a **Bimodal Execution Topology**. We decoupled the deterministic physics (Guardrails compiled from SysML v2 property blocks into fast Pydantic models) from the cognitive observation (the Claude API).
*   **Result:** This mathematically bounds the blast radius of LLM hallucinations. The system achieves 0% requirements drift and sub-millisecond guardrail execution.

### 2.2 SQLite vs. PostgreSQL for Edge Audit Logging (DR-AIS)
*   **Original Concept:** Deploy a Postgres container alongside the SafeACS stack for robust, concurrent audit logging of the DR-AIS (Deterministic Risk - AI Safety) ledger.
*   **Trade-off Analysis:** A full Postgres deployment severely impacted the Size, Weight, and Power (SWaP) budget of the Jetson module. The memory overhead increased by ~400MB, threatening the thermal throttling limits during high-frequency telemetry bursts.
*   **CDR Decision:** Downgrade to **SQLite 3** operating in Write-Ahead Logging (WAL) mode.
*   **Result:** Concurrency needs at the edge were strictly sequential (single daemon writing telemetry). SQLite WAL mode easily saturated the necessary 100Hz write-speed with a 5MB memory footprint.

### 2.3 Cloud Inference vs. Edge Inference (Cognitive Layer)
*   **Original Concept:** Run the AI Heuristic Engine entirely locally on the Jetson Orin Nano using quantized 4-bit models to maintain zero-trust network isolation.
*   **Trade-off Analysis:** The Jetson Orin Nano possesses 8GB of shared RAM/VRAM. Loading a 7B parameter model consumed 4.5GB, leaving insufficient headroom for the OS, simulator, and high-frequency Pydantic evaluation processes. Context windows were also restricted, removing the ability to do complex chain-of-thought diagnostics on the telemetry history.
*   **CDR Decision:** Hybrid Edge-Cloud. The deterministic Guardrails run 100% locally on the Edge (air-gapped logic). The Heuristic Engine was offloaded to the **Anthropic Claude API** via secure TLS. If connection is lost, the system gracefully degrades to static deterministic control (PID loops).
*   **Result:** Ensured strict real-time safety locally, while leveraging massive Tier-1 foundation models for complex anomaly detection.

## 3. System Decomposition & Interfaces

The system was formally decomposed into the following Container Boundaries:

1.  **Telemetry Gateway (Python/FastAPI):** Ingests raw sensor streams (UDP/REST).
2.  **Structural Guardrails (Pydantic):** Auto-generated validation schemas derived directly from SysML v2 property bounds (e.g., `max_rpm <= 6000`).
3.  **Decision Protocol Router:** The asynchronous middle-ware that evaluates whether proposed mitigations are Type 1 (Irreversible - requires human-in-the-loop) or Type 2 (Reversible - autonomous execution).

## 4. Unresolved Risks & Future Work

*   **Risk (Medium):** The Streamlit Ground Station UI polling mechanism (via `deque` buffers) is acceptable for the MVP but will block at enterprise scale (10k+ Hz). 
*   **Mitigation:** Transition to standard WebSockets for the UI telemetry link in v2.0.
