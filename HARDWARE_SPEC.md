# Hardware Specification: SafeACS Edge Node

**Component:** SafeACS Compute Engine
**Target Platform:** NVIDIA Jetson Orin Nano (8GB)
**Domain:** Cyber-Physical Aerospace / Defense Systems

## 1. Subsystem Overview
The SafeACS Compute Engine acts as the primary deterministic boundary and AI heuristic gateway for mission-critical cyber-physical systems. To guarantee the real-time, 50ms control loop for the Attitude Control System (ACS), the compute node must meet stringent Size, Weight, Power, and Cost (SWaP-C) limitations while surviving hostile mission environments.

## 2. Theoretical SWaP-C Constraints
*   **Size:** 69.6 mm x 45 mm (SOM footprint)
*   **Weight:** < 50 grams (compute module only; excluding custom passive heatsink)
*   **Power (TDP):** Configurable 7W to 15W max.
    *   *Constraint:* The spacecraft bus allocates a strict 12W budget for the payload compute. The Jetson Orin Nano must be software-constrained (`nvpmodel -m 1`) to the 10W power profile to prevent bus brownouts during active Claude API inferencing/network transmission.

## 3. Environmental & Mechanical Constraints

### 3.1 Thermal Engineering
*   **Operating Temperature Range:** -25°C to +90°C (Measured at the Thermal Transfer Plate / TTP).
*   **Dissipation Strategy:** Conduction cooling only. Active cooling (fans) is strictly prohibited due to mechanical failure rates in vacuum/high-vibration environments. The SOM must be mechanically mated to the chassis structural bulkhead via a custom Aluminum Nitride (AlN) thermal pad to dissipate up to 10W of transient heat load.

### 3.2 Vibration and Shock
*   **Operational Vibration:** 5 Grms (Random, 10 Hz to 2000 Hz) per MIL-STD-810H Method 514.8.
*   **Mechanical Shock:** 50 G, 11ms half-sine pulse per MIL-STD-810H Method 516.8 (simulating launch separation pyrotechnics).
*   *Mitigation:* The 260-pin SO-DIMM connector must be organically staked (using aerospace-grade epoxy like Araldite 2011) post-insertion to prevent catastrophic disconnection during launch kinematics.

### 3.3 EMI / EMC (Electromagnetic Interference)
*   **Standard:** MIL-STD-461G (CE102, RE102, RS103).
*   **Constraint:** The high-frequency signaling of the Orin Nano's LPDDR5 memory (up to 68 GB/s bandwidth) presents a severe radiated emissions (RE) risk to the spacecraft's S-band communication transceivers.
*   **Mitigation:** The entire compute module must be enclosed in a Faraday cage (machined aluminum 6061-T6 housing) with specialized RF gaskets on all mating surfaces. All external I/O (Ethernet, Serial) must pass through inline EMI suppression filters before exiting the housing.

### 3.4 Radiation Tolerance (Space Environments)
*   The Jetson Orin Nano is Commercial Off-The-Shelf (COTS) and is **not** inherently rad-hard.
*   **Mitigation:** For Low Earth Orbit (LEO) deployment, the module relies on system-level shielding (Al chassis) and architectural fault tolerance. The deterministic SafeACS software architecture assumes Single Event Upsets (SEUs) will corrupt memory. If the deterministic Guardrail process crashes due to a bit-flip, the ACS hardware automatically defaults to the analog safe-mode PID loop until the watchdog timer reboots the Jetson SOM.
