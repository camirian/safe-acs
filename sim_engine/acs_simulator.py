"""
sim_engine/acs_simulator.py

Synthetic Attitude Control System (ACS) Simulator.
Generates high-fidelity telemetry simulating a 3-axis stabilized satellite
utilizing a reaction wheel array and gyroscope subsystem.

Designed for edge-compute AI guardrail assurance testing.
"""

import time
import json
import random
import math
from dataclasses import dataclass, asdict

@dataclass
class Quaternion:
    w: float
    x: float
    y: float
    z: float

@dataclass
class AngularRates:
    roll: float
    pitch: float
    yaw: float

@dataclass
class ReactionWheelsRPM:
    wheel_1: float
    wheel_2: float
    wheel_3: float

@dataclass
class ACSTelemetry:
    timestamp_ns: int
    attitude_q: Quaternion
    angular_rates: AngularRates
    rw_rpms: ReactionWheelsRPM

class ACSSimulator:
    """
    3-Axis Stabilized Satellite ACS Simulator.
    Outputs high-frequency JSON telemetry representing the current physical state.
    """

    def __init__(self, frequency_hz: float = 100.0):
        # Simulation parameters
        self.frequency_hz: float = frequency_hz
        self.dt: float = 1.0 / self.frequency_hz
        
        # Initial nominal states
        self.attitude = Quaternion(1.0, 0.0, 0.0, 0.0)
        self.rates = AngularRates(0.0, 0.0, 0.0)
        
        # Reaction wheel nominal RPMs (baseline)
        self.rw_rpms = ReactionWheelsRPM(
            wheel_1=2000.0,
            wheel_2=2000.0,
            wheel_3=2000.0
        )
        
        # Anomaly simulation state (KINETIC-TWIN Element)
        self.anomaly_active: bool = False
        self.anomaly_drift_rate: float = 0.0 # RPM per second
        self.target_anomaly_wheel: int = 2
        
    def inject_anomaly(self, wheel_index: int = 2, drift_rate_rpm: float = 5.0) -> None:
        """
        Activates a micro-deviation trajectory in the specified reaction wheel.
        This tests the prompt heuristic anomaly detection without immediately triggering
        the deterministic structural constraint limit.
        
        Args:
            wheel_index (int): The index of the wheel to fail (1, 2, or 3).
            drift_rate_rpm (float): The rate at which the wheel RPM deviates per second.
        """
        self.anomaly_active = True
        self.target_anomaly_wheel = wheel_index
        self.anomaly_drift_rate = drift_rate_rpm
    
    def clear_anomaly(self) -> None:
        """Deactivates any ongoing micro-deviation."""
        self.anomaly_active = False
        self.anomaly_drift_rate = 0.0

    def _update_physics(self) -> None:
        """
        Steps the physical simulation forward by self.dt.
        Applies orbital disturbances, sensor noise, and any active anomalies.
        """
        # 1. Apply baseline sensor noise (Gaussian)
        noise_std = 0.001
        self.rates.roll += random.gauss(0.0, noise_std) * self.dt
        self.rates.pitch += random.gauss(0.0, noise_std) * self.dt
        self.rates.yaw += random.gauss(0.0, noise_std) * self.dt
        
        # 2. Update RPM based on active anomalies
        if self.anomaly_active:
            drift_step = self.anomaly_drift_rate * self.dt
            if self.target_anomaly_wheel == 1:
                self.rw_rpms.wheel_1 += drift_step
            elif self.target_anomaly_wheel == 2:
                self.rw_rpms.wheel_2 += drift_step
            elif self.target_anomaly_wheel == 3:
                self.rw_rpms.wheel_3 += drift_step
                
        # 3. Naive kinematic integration for quaternion attitude
        w, x, y, z = self.attitude.w, self.attitude.x, self.attitude.y, self.attitude.z
        wx, wy, wz = self.rates.roll, self.rates.pitch, self.rates.yaw
        
        dw = -0.5 * (x * wx + y * wy + z * wz)
        dx =  0.5 * (w * wx - z * wy + y * wz)
        dy =  0.5 * (z * wx + w * wy - x * wz)
        dz = -0.5 * (y * wx + x * wy + w * wz)
        
        self.attitude.w += dw * self.dt
        self.attitude.x += dx * self.dt
        self.attitude.y += dy * self.dt
        self.attitude.z += dz * self.dt
        
        # Normalize quaternion to prevent numerical drift
        norm = math.sqrt(
            self.attitude.w**2 + self.attitude.x**2 + 
            self.attitude.y**2 + self.attitude.z**2
        )
        if norm > 0:
            self.attitude.w /= norm
            self.attitude.x /= norm
            self.attitude.y /= norm
            self.attitude.z /= norm

    def get_telemetry(self) -> ACSTelemetry:
        """Retrieves current physical state as structured telemetry object."""
        return ACSTelemetry(
            timestamp_ns=time.time_ns(),
            attitude_q=Quaternion(**asdict(self.attitude)),
            angular_rates=AngularRates(**asdict(self.rates)),
            rw_rpms=ReactionWheelsRPM(**asdict(self.rw_rpms))
        )

    def generate_telemetry_json(self) -> str:
        """Returns the current telemetry frame as a serialized JSON string."""
        return json.dumps(asdict(self.get_telemetry()))

    def run_step(self) -> str:
        """
        Executes a single simulation tick and returns the raw JSON telemetry.
        Intended to operate at frequency_hz.
        """
        self._update_physics()
        return self.generate_telemetry_json()

if __name__ == "__main__":
    # Example standalone execution footprint
    sim = ACSSimulator(frequency_hz=10.0) # Downsampled for human readability
    print("--- Starting Nominal Synthetic ACS Telemetry Stream ---")
    
    try:
        for _ in range(3):
            print(sim.run_step())
            time.sleep(sim.dt)
            
        print("\n--- Injecting Drift Anomaly on Wheel 2 ---")
        sim.inject_anomaly(wheel_index=2, drift_rate_rpm=50.0)
        
        for _ in range(3):
            print(sim.run_step())
            time.sleep(sim.dt)
            
    except KeyboardInterrupt:
        print("\nSimulation halted by user.")
