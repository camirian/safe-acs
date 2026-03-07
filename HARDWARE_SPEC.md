# SafeACS Hardware Subsystem Specification

**Configuration Item:** H2 (Edge Assurance Node)  
**Target Hardware:** NVIDIA Jetson Orin Nano (8GB)  
**Standard References:** MIL-STD-810H (Environmental), MIL-STD-461G (EMI/EMC)

## 1. Executive Summary
The SafeACS Edge Assurance Node (Configuration Item H2) acts as the deterministic mission assurance boundary between the probabilistic Artificial Intelligence (Cloud) and the physical actuators (Space Vehicle). This document formalizes the hardware specifications, environmental engineering constraints, and physical interface controls required for the Jetson Orin Nano to operate safely in a simulated LEO (Low Earth Orbit) deployment.

## 2. Power and SWaP-C Constraints
The selection of the NVIDIA Jetson Orin Nano rests fundamentally upon its Size, Weight, Power, and Cost (SWaP-C) profile. 

*   **Size:** 69.6 mm x 45 mm (SO-DIMM envelope).
*   **Weight:** < 50 grams (compute module only).
*   **Power:** Configurable 7W to 15W TDP.
    *   *Constraint Mitigation:* The 15W envelope is well within the power budget of a standard 3U to 6U CubeSat EPS (Electrical Power System) while still providing 40 TOPS of AI performance for the Bimodal Decision Protocol routing.

## 3. Environmental Engineering (MIL-STD-810H)
To be certified for flight operations, the Edge Node enclosure and mounting must satisfy rigorous environmental testing profiles.

### 3.1 Thermal Management (Method 501.7 / 502.7)
*   **Operating Range (Module):** -25°C to 90°C.
*   **Space Vacuum Constraint:** Convective cooling (fans) is impossible in orbit. 
*   **Engineering Solution:** The Jetson module must be thermally coupled to the Space Vehicle's chassis via a highly conductive thermal pad and a custom-machined aluminum heat spreader. Heat is dissipated purely through **conduction** to the spacecraft body and subsequent radiation into deep space.

### 3.2 Vibration and Shock (Method 514.8 / 516.8)
*   **Condition:** Launch vehicle ascent exposes the node to extreme random vibration.
*   **Constraint:** The SO-DIMM edge connector is susceptible to fretting corrosion and dislodgement under high G-forces.
*   **Engineering Solution:** The compute module must be secured to the carrier board using dual locking standoffs with low-outgassing threadlocker (e.g., Loctite 222). Additionally, the carrier board must be conformal-coated to dampen harmonic resonance across the PCB.

### 3.3 EMI / EMC (MIL-STD-461G)
*   **Condition:** The space environment is subjected to high radiation, and the spacecraft itself generates significant electromagnetic noise (e.g., from the reaction wheels and transceivers).
*   **Constraint:** Electromagnetic interference could induce bit-flips in the RAM, corrupting the deterministic Pydantic guardrails.
*   **Engineering Solution:** The entire Edge Node assembly must be housed in an RF-shielded Faraday enclosure. All external wiring harnesses must use shielded twisted pairs.

## 4. Interface Control Document (ICD)
The following table defines the physical and data link interfaces bridging the Edge Node (H2) to the Space and Ground Segments.

| Interface ID | Connected Element | Physical Layer | Protocol | Data Rate | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **IF-01** | ACS Hardware (H1) | RS-422 / LVDS | Custom JSON over Serial | 115200 baud | High-frequency ingestion of raw telemetry from reaction wheels and gyros. |
| **IF-02** | ACS Hardware (H1) | RS-422 | PWM / DAC | 9600 baud | Transmission of deterministic, zero-drift actuation commands (override signals). |
| **IF-03** | SatCom Transceiver | SpaceWire / Ethernet | TCP/IP | 10 Mbps+ | Outbound transmission of telemetry to the Ground Station (H3) and the Claude API. |
| **IF-04** | SatCom Transceiver | SpaceWire / Ethernet | TCP/IP | 10 Mbps+ | Inbound receipt of cryptographic signatures from the human-in-the-loop operator. |

## 5. Architectural Alignment
This hardware specification directly supports the software architecture defined in `ARCHITECTURE.md`. By constraining the physical hardware to deterministic interfaces (RS-422) and implementing strict EMI shielding, the system guarantees that the auto-generated Pydantic guardrails will execute exactly as defined by the original MBSE SysML models, without physical or electrical degradation.
