"""
edge_node/guardrails.py

Deterministic Hardware Safety Guardrails for the SafeACS Edge Node.

These Pydantic models represent the COMPILED OUTPUT of the SysML v2 MBSE pipeline.
Each `Field` constraint is a direct 1:1 trace to a physical hardware attribute limit
defined in the SysML v2 PartDefinition for the Satellite ACS subsystem.

ZERO-DRIFT PRINCIPLE: No modification to these constraints is permitted without first
updating the upstream SysML v2 property block and regenerating this file via the
CI/CD pipeline. Manual edits constitute a Requirements Traceability violation.

Traceability:
    SysML v2 Source: ACS::ReactionWheelAssembly -> max_rpm (AttributeUsage)
    SysML v2 Source: ACS::Gyroscope -> max_angular_rate_deg_s (AttributeUsage)
    SysML v2 Source: ACS::AttitudeSolution -> quaternion_norm_tolerance (ConstraintUsage)

Standards: DO-178C (Software Correctness), MIL-STD-882 (Hazard Mitigation)
"""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field, model_validator
from typing import Optional
import math


# ---------------------------------------------------------------------------
# Violation Severity Taxonomy
# Aligned with MIL-STD-882 Hazard Probability/Severity Matrix
# ---------------------------------------------------------------------------

class ViolationSeverity(str, Enum):
    """MIL-STD-882 Severity Classification for constraint violations."""
    CATASTROPHIC = "CATASTROPHIC"   # Loss of life / hardware destruction
    CRITICAL = "CRITICAL"           # Major system damage, mission failure
    MARGINAL = "MARGINAL"           # Reduced mission performance
    NEGLIGIBLE = "NEGLIGIBLE"       # No significant impact


class ViolationType(str, Enum):
    """Bimodal action classification. Determines human-in-the-loop requirement."""
    TYPE_1_IRREVERSIBLE = "TYPE_1_IRREVERSIBLE"   # Requires human cryptographic approval
    TYPE_2_REVERSIBLE = "TYPE_2_REVERSIBLE"        # Autonomous mitigation permitted


# ---------------------------------------------------------------------------
# Guardrail Violation Report
# ---------------------------------------------------------------------------

class GuardrailViolation(BaseModel):
    """
    Structured violation record emitted when a telemetry attribute breaches
    a SysML-derived constraint. Directly feeds the DR-AIS immutable audit log.
    """
    field: str
    observed_value: float
    limit_value: float
    severity: ViolationSeverity
    action_type: ViolationType
    message: str


# ---------------------------------------------------------------------------
# SysML v2 Attribute Usage Guardrails
# Each Pydantic Field constraint = one SysML v2 AttributeUsage constraint
# ---------------------------------------------------------------------------

class MomentumWheelStateGuardrail(BaseModel):
    """
    Pydantic guardrail for a single Reaction Wheel assembly.
    Typed by SysML v2 PartDefinition: ACS::ReactionWheelAssembly

    Physical constraint: Structural disintegration occurs above 6000 RPM.
    HZ-001 Mitigation: Command drop + immediate safe-mode PID fallback.
    """
    wheel_id: int = Field(..., description="Wheel index (1, 2, or 3)")
    rpm: float = Field(
        ...,
        ge=-6000.0,   # SysML v2 AttributeUsage: min_rpm = -6000 (bidirectional spin)
        le=6000.0,    # SysML v2 AttributeUsage: max_rpm = 6000
        description="Reaction wheel angular velocity (RPM). Structural limit: ±6000."
    )

    def check(self) -> Optional[GuardrailViolation]:
        """Evaluates this wheel's RPM against its structural constraint."""
        if abs(self.rpm) > 6000.0:
            return GuardrailViolation(
                field=f"rw_rpms.wheel_{self.wheel_id}",
                observed_value=self.rpm,
                limit_value=6000.0,
                severity=ViolationSeverity.CATASTROPHIC,
                action_type=ViolationType.TYPE_1_IRREVERSIBLE,
                message=(
                    f"FATAL: Wheel {self.wheel_id} RPM {self.rpm:.2f} exceeds "
                    f"structural limit ±6000 RPM. Immediate PID fallback required."
                )
            )
        return None


class AngularRateGuardrail(BaseModel):
    """
    Pydantic guardrail for the 3-axis Gyroscope assembly.
    Typed by SysML v2 PartDefinition: ACS::Gyroscope

    Physical constraint: Control loop instability occurs above ±5 deg/s on any axis.
    HZ-002 Mitigation: Rate clamping + API watchdog timeout.
    """
    roll: float = Field(
        ...,
        ge=-5.0,   # SysML v2 AttributeUsage: max_angular_rate_roll_deg_s
        le=5.0,
        description="Roll angular rate (deg/s). Control stability limit: ±5."
    )
    pitch: float = Field(
        ...,
        ge=-5.0,   # SysML v2 AttributeUsage: max_angular_rate_pitch_deg_s
        le=5.0,
        description="Pitch angular rate (deg/s). Control stability limit: ±5."
    )
    yaw: float = Field(
        ...,
        ge=-5.0,   # SysML v2 AttributeUsage: max_angular_rate_yaw_deg_s
        le=5.0,
        description="Yaw angular rate (deg/s). Control stability limit: ±5."
    )

    def check(self) -> list[GuardrailViolation]:
        """Evaluates all three angular rate axes against their structural constraints."""
        violations: list[GuardrailViolation] = []
        for axis, value in [("roll", self.roll), ("pitch", self.pitch), ("yaw", self.yaw)]:
            if abs(value) > 5.0:
                violations.append(GuardrailViolation(
                    field=f"angular_rates.{axis}",
                    observed_value=value,
                    limit_value=5.0,
                    severity=ViolationSeverity.CRITICAL,
                    action_type=ViolationType.TYPE_1_IRREVERSIBLE,
                    message=(
                        f"CRITICAL: {axis.capitalize()} rate {value:.4f} deg/s exceeds "
                        f"control stability limit ±5 deg/s."
                    )
                ))
        return violations


class QuaternionNormGuardrail(BaseModel):
    """
    Pydantic guardrail for attitude solution quaternion integrity.
    Typed by SysML v2 PartDefinition: ACS::AttitudeSolution

    Constraint: A unit quaternion must satisfy |q|² = 1.0 within tolerance.
    Deviation indicates numerical divergence or corrupted sensor data (HZ-005).
    """
    w: float
    x: float
    y: float
    z: float

    @model_validator(mode='after')
    def validate_norm(self) -> 'QuaternionNormGuardrail':
        norm = math.sqrt(self.w**2 + self.x**2 + self.y**2 + self.z**2)
        tolerance = 0.01  # SysML v2 ConstraintUsage: quaternion_norm_tolerance
        if abs(norm - 1.0) > tolerance:
            raise ValueError(
                f"FATAL: Quaternion norm {norm:.6f} deviates from unit constraint "
                f"beyond tolerance ±{tolerance}. Possible sensor corruption (HZ-005)."
            )
        return self

    def check(self) -> Optional[GuardrailViolation]:
        """Evaluates quaternion norm integrity."""
        norm = math.sqrt(self.w**2 + self.x**2 + self.y**2 + self.z**2)
        if abs(norm - 1.0) > 0.01:
            return GuardrailViolation(
                field="attitude_q.norm",
                observed_value=norm,
                limit_value=1.0,
                severity=ViolationSeverity.CATASTROPHIC,
                action_type=ViolationType.TYPE_1_IRREVERSIBLE,
                message=(
                    f"FATAL: Quaternion norm {norm:.6f} violates unit constraint. "
                    f"Possible telemetry corruption or schema injection (HZ-005)."
                )
            )
        return None


# ---------------------------------------------------------------------------
# Top-Level Telemetry Guardrail
# Aggregates all attribute-level checks into a single evaluation report
# ---------------------------------------------------------------------------

class ACSTelemetryGuardrailReport(BaseModel):
    """
    Structured evaluation report for a single ACS telemetry frame.
    Produced by the GuardrailEngine for every incoming telemetry tick.
    """
    passed: bool
    violations: list[GuardrailViolation] = Field(default_factory=list)
    has_fatal_violation: bool = False
    requires_type_1_action: bool = False


class GuardrailEngine:
    """
    Deterministic Structural Constraint Evaluator.

    Evaluates every incoming telemetry frame against all SysML-derived Pydantic
    constraints. Produces a structured ACSTelemetryGuardrailReport.

    This is the zero-drift barrier. It runs synchronously on the edge node before
    any telemetry is forwarded to the probabilistic LLM layer.
    """

    def evaluate(self, telemetry: dict) -> ACSTelemetryGuardrailReport:
        """
        Args:
            telemetry (dict): Raw parsed JSON telemetry frame from the ACS simulator.

        Returns:
            ACSTelemetryGuardrailReport: Full constraint evaluation with all violations.
        """
        violations: list[GuardrailViolation] = []

        # --- Evaluate Quaternion Norm (HZ-005 Corruption Guard) ---
        try:
            q = telemetry.get("attitude_q", {})
            q_guard = QuaternionNormGuardrail(**q)
            qv = q_guard.check()
            if qv:
                violations.append(qv)
        except Exception as e:
            violations.append(GuardrailViolation(
                field="attitude_q",
                observed_value=0.0,
                limit_value=1.0,
                severity=ViolationSeverity.CATASTROPHIC,
                action_type=ViolationType.TYPE_1_IRREVERSIBLE,
                message=f"FATAL: Quaternion schema validation failed: {e}"
            ))

        # --- Evaluate Angular Rates (HZ-002 Rate Guard) ---
        try:
            ar = telemetry.get("angular_rates", {})
            ar_guard = AngularRateGuardrail(**ar)
            violations.extend(ar_guard.check())
        except Exception as e:
            violations.append(GuardrailViolation(
                field="angular_rates",
                observed_value=0.0,
                limit_value=5.0,
                severity=ViolationSeverity.CRITICAL,
                action_type=ViolationType.TYPE_1_IRREVERSIBLE,
                message=f"CRITICAL: Angular rate schema validation failed: {e}"
            ))

        # --- Evaluate Reaction Wheel RPMs (HZ-001 Structural Guard) ---
        rw = telemetry.get("rw_rpms", {})
        for i, (key, rpm_value) in enumerate(rw.items(), start=1):
            try:
                wheel = MomentumWheelStateGuardrail(wheel_id=i, rpm=rpm_value)
                violation = wheel.check()
                if violation:
                    violations.append(violation)
            except Exception as e:
                violations.append(GuardrailViolation(
                    field=f"rw_rpms.wheel_{i}",
                    observed_value=0.0,
                    limit_value=6000.0,
                    severity=ViolationSeverity.CATASTROPHIC,
                    action_type=ViolationType.TYPE_1_IRREVERSIBLE,
                    message=f"FATAL: Wheel {i} schema validation failed: {e}"
                ))

        has_fatal = any(
            v.severity == ViolationSeverity.CATASTROPHIC for v in violations
        )
        requires_type_1 = any(
            v.action_type == ViolationType.TYPE_1_IRREVERSIBLE for v in violations
        )

        return ACSTelemetryGuardrailReport(
            passed=len(violations) == 0,
            violations=violations,
            has_fatal_violation=has_fatal,
            requires_type_1_action=requires_type_1,
        )
