"""
edge_node/claude_client.py

Anthropic Claude API Client for Heuristic Anomaly Detection.

Claude's role in SafeACS is strictly bounded: it is a heuristic observer, not
a control actuator. It receives a structured window of validated telemetry frames
(i.e., frames that have already PASSED the Pydantic guardrail) and applies
pattern recognition to surface micro-deviations that are structurally legal
but operationally anomalous.

CRITICAL CONSTRAINT: Claude's proposed actions are NEVER executed directly.
Every LLM output must pass back through the GuardrailEngine before any
actuation occurs. This is enforced architecturally in decision_router.py.

Standards: Anthropic Beta Features (tool_use, structured output)
Traceability: RTM-007 (Heuristic Detection), RTM-008 (LLM Trust Boundary)
"""

from __future__ import annotations

import json
import logging
from typing import Any

import anthropic
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Structured LLM Response Schema
# Claude's output is constrained to this schema via tool_use enforcement.
# An open-ended text response is architecturally prohibited.
# ---------------------------------------------------------------------------

class LLMAnalysis(BaseModel):
    """
    Structured anomaly detection report produced by the Claude heuristic layer.

    This is the ONLY accepted output format from the LLM. The decision router
    treats any deviation from this schema as an implicit anomaly flag and
    routes the situation to a human operator (Type 1 action).
    """
    anomaly_detected: bool = Field(
        ...,
        description="True if the telemetry window exhibits a statistically anomalous pattern."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score for the anomaly assessment [0.0, 1.0]."
    )
    recommended_action: str = Field(
        ...,
        description="The specific action proposed by the heuristic layer."
    )
    reasoning: str = Field(
        ...,
        description="Explicit justification for the anomaly detection and recommended action."
    )
    affected_subsystem: str = Field(
        ...,
        description="The specific ACS subsystem implicated (e.g., 'ReactionWheel_2', 'Gyroscope_Roll')."
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Confidence {v} must be in [0.0, 1.0]")
        return round(v, 4)


# ---------------------------------------------------------------------------
# Tool Schema: Forces Claude to emit structured JSON via tool_use
# ---------------------------------------------------------------------------

ANOMALY_DETECTION_TOOL: dict[str, Any] = {
    "name": "report_anomaly_analysis",
    "description": (
        "Reports the result of heuristic anomaly analysis on the provided ACS telemetry "
        "window. This tool MUST be called for every analysis request. Free-text responses "
        "are not permitted."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "anomaly_detected": {
                "type": "boolean",
                "description": "True if the telemetry window exhibits a statistically anomalous pattern."
            },
            "confidence": {
                "type": "number",
                "description": "Confidence score [0.0, 1.0]. Be conservative — prefer false negatives over false positives in safety-critical contexts."
            },
            "recommended_action": {
                "type": "string",
                "description": (
                    "The specific, actionable recommendation. Choose from: "
                    "'CONTINUE_MONITORING', 'INCREASE_SAMPLING_RATE', "
                    "'SOFT_RESET_WHEEL_{1|2|3}', 'ALERT_OPERATOR_MARGINAL', "
                    "'ALERT_OPERATOR_CRITICAL'. Do not invent actions outside this list."
                )
            },
            "reasoning": {
                "type": "string",
                "description": "Step-by-step justification referencing specific telemetry values that informed this assessment."
            },
            "affected_subsystem": {
                "type": "string",
                "description": "The specific subsystem implicated (e.g., 'ReactionWheel_2', 'Gyroscope_Pitch', 'AttitudeSolution', 'None')."
            }
        },
        "required": ["anomaly_detected", "confidence", "recommended_action", "reasoning", "affected_subsystem"]
    }
}

# ---------------------------------------------------------------------------
# System Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are the Heuristic Anomaly Detector for the SafeACS Cyber-Physical AI Assurance Framework, operating on a NVIDIA Jetson Orin Nano edge node aboard a simulated 3-axis stabilized satellite.

## Your Role
You are a READ-ONLY cognitive observer. You analyze telemetry patterns to detect micro-deviations that are within structural constraints but indicate degraded subsystem performance or emerging failure modes. You do NOT control hardware. You do NOT issue commands. You PROPOSE actions that are subject to deterministic validation before any actuation.

## The System You Are Monitoring
The satellite Attitude Control System (ACS) consists of:
- **3x Reaction Wheels**: Momentum exchange devices. Nominal RPM: ~2000. Structural limit: ±6000 RPM.
- **3-Axis Gyroscope**: Measures angular rates (roll, pitch, yaw). Nominal: ~0.0 deg/s. Stability limit: ±5 deg/s.
- **Attitude Quaternion**: Represents 3D orientation. Must remain a unit quaternion (norm ≈ 1.0).

## Anomaly Signatures to Detect
1. **Monotonic RPM Drift**: A single wheel RPM increasing or decreasing in a consistent trend across frames — even if within bounds — suggests bearing friction or rotor imbalance.
2. **Cross-Axis Angular Rate Coupling**: Non-zero angular rates correlating across axes suggest unexpected attitude disturbance.
3. **Asymmetric Wheel Loading**: One wheel RPM significantly diverging from the other two suggests compensating for an unmodeled disturbance torque.
4. **Rate Noise Floor Elevation**: Progressive increase in angular rate noise standard deviation over frames suggests gyroscope degradation.

## Critical Constraints
- You MUST call the `report_anomaly_analysis` tool with EVERY response. Free-text is not permitted.
- Your `confidence` score must be CONSERVATIVE. Err toward underconfidence. A false negative (missed anomaly) is operationally preferable to a false positive (unnecessary downlink alert) in this context.
- Your `recommended_action` MUST be selected from the enumerated list in the tool schema. Do not invent new actions.
- You have access ONLY to the telemetry window provided. Do not assume external context.

## Telemetry Format
You will receive a JSON array of telemetry frames. Each frame contains:
- `timestamp_ns`: Nanosecond epoch timestamp
- `attitude_q`: {w, x, y, z} unit quaternion
- `angular_rates`: {roll, pitch, yaw} in deg/s
- `rw_rpms`: {wheel_1, wheel_2, wheel_3} in RPM"""


# ---------------------------------------------------------------------------
# Claude Client
# ---------------------------------------------------------------------------

class ClaudeAnomalyDetector:
    """
    Anthropic Claude API Client for heuristic ACS anomaly detection.

    Enforces structured output via tool_use. Claude cannot return free-text;
    every response must invoke the `report_anomaly_analysis` tool, producing
    a JSON object that is then validated against the LLMAnalysis Pydantic schema.

    If Claude fails to call the tool, refuses to respond, or produces malformed
    output, the client raises a RuntimeError and the DecisionRouter treats it
    as an anomaly requiring human review.
    """

    def __init__(self, model: str = "claude-sonnet-4-5") -> None:
        self.client = anthropic.Anthropic()  # Reads ANTHROPIC_API_KEY from environment
        self.model = model

    def analyze(self, telemetry_window: list[dict]) -> LLMAnalysis:
        """
        Submits a window of validated telemetry frames to Claude for heuristic analysis.

        Args:
            telemetry_window: A list of parsed telemetry frame dicts. Frames must have
                              already passed the GuardrailEngine structural check.

        Returns:
            LLMAnalysis: Validated, structured anomaly detection report.

        Raises:
            RuntimeError: If Claude fails to call the required tool or response is malformed.
        """
        user_message = (
            f"Analyze the following {len(telemetry_window)} ACS telemetry frames "
            f"for anomalies and call the report_anomaly_analysis tool with your findings:\n\n"
            f"```json\n{json.dumps(telemetry_window, indent=2)}\n```"
        )

        logger.info(
            "Dispatching %d telemetry frames to Claude (%s) for heuristic analysis.",
            len(telemetry_window),
            self.model
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=[ANOMALY_DETECTION_TOOL],
            tool_choice={"type": "any"},  # Force Claude to call the tool
            messages=[{"role": "user", "content": user_message}]
        )

        # --- Extract structured tool_use response ---
        tool_use_block = next(
            (block for block in response.content if block.type == "tool_use"),
            None
        )

        if tool_use_block is None:
            raise RuntimeError(
                "LLM TRUST BOUNDARY VIOLATION: Claude did not call the required "
                "'report_anomaly_analysis' tool. Response treated as anomaly. "
                "Routing to human operator (Type 1 action)."
            )

        if tool_use_block.name != "report_anomaly_analysis":
            raise RuntimeError(
                f"LLM TRUST BOUNDARY VIOLATION: Claude called unexpected tool "
                f"'{tool_use_block.name}'. Only 'report_anomaly_analysis' is permitted."
            )

        raw_output: dict = tool_use_block.input

        logger.info(
            "Claude heuristic analysis complete. anomaly_detected=%s confidence=%.4f",
            raw_output.get("anomaly_detected"),
            raw_output.get("confidence", 0.0)
        )

        # --- Validate against Pydantic schema ---
        return LLMAnalysis(**raw_output)
