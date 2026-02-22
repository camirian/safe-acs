"""
edge_node/decision_router.py

Bimodal Decision Protocol Router for the SafeACS Edge Node.

This module is the architectural heart of the SafeACS framework. It orchestrates
the deterministic-first, heuristic-second execution topology defined in ARCHITECTURE.md.

Execution Flow (per telemetry tick):
  1. Ingest raw JSON telemetry from the Synthetic ACS simulator.
  2. [DETERMINISTIC LAYER] Pass telemetry through GuardrailEngine constraint checks.
     - If FATAL violation detected: emit immediate safe-mode override. Skip LLM entirely.
  3. [HEURISTIC LAYER] If telemetry is structurally nominal, accumulate a telemetry
     window and periodically dispatch it to ClaudeAnomalyDetector for pattern analysis.
  4. [SECOND GUARDRAIL PASS] Any action proposed by Claude is re-evaluated against
     the Pydantic constraints. Claude CANNOT bypass the deterministic layer.
  5. [ACTUATION] Emit a structured DecisionEvent for the audit log and downstream systems.

Standards: DO-178C Section 6.3 (Traceability), MIL-STD-882 Table II (Risk Assessment)
Traceability: RTM-003 (Bimodal Protocol), RTM-007 (Heuristic Detection), RTM-009 (Audit)
"""

from __future__ import annotations

import json
import logging
import time
from collections import deque
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from edge_node.guardrails import (
    ACSTelemetryGuardrailReport,
    GuardrailEngine,
    GuardrailViolation,
    ViolationSeverity,
    ViolationType,
)
from edge_node.claude_client import ClaudeAnomalyDetector, LLMAnalysis

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Decision Protocol Outcome Taxonomy
# ---------------------------------------------------------------------------

class DecisionOutcome(str, Enum):
    """
    Enumerates the possible outcomes of the bimodal decision protocol.
    Each outcome corresponds to a specific execution path in the sequence diagram.
    """
    GUARDRAIL_PASS_LLM_SKIPPED = "GUARDRAIL_PASS_LLM_SKIPPED"
    """Telemetry nominal. No anomaly detected yet. LLM window not full."""

    GUARDRAIL_PASS_LLM_NOMINAL = "GUARDRAIL_PASS_LLM_NOMINAL"
    """Telemetry nominal. LLM window dispatched. No anomaly detected."""

    GUARDRAIL_PASS_LLM_ANOMALY_TYPE2 = "GUARDRAIL_PASS_LLM_ANOMALY_TYPE2"
    """Telemetry nominal. LLM detected anomaly. Reversible Type 2 action emitted."""

    GUARDRAIL_PASS_LLM_ANOMALY_TYPE1 = "GUARDRAIL_PASS_LLM_ANOMALY_TYPE1"
    """Telemetry nominal. LLM detected anomaly. Irreversible — human approval required."""

    GUARDRAIL_VIOLATION_FATAL = "GUARDRAIL_VIOLATION_FATAL"
    """Fatal structural constraint violated. LLM bypassed. Immediate safe-mode override."""

    GUARDRAIL_VIOLATION_CRITICAL = "GUARDRAIL_VIOLATION_CRITICAL"
    """Critical structural constraint violated. Human operator alert (Type 1)."""

    LLM_TRUST_BOUNDARY_VIOLATION = "LLM_TRUST_BOUNDARY_VIOLATION"
    """Claude failed to produce valid structured output. Route to human review."""


# ---------------------------------------------------------------------------
# Decision Event: Structured Audit Record
# ---------------------------------------------------------------------------

class DecisionEvent(BaseModel):
    """
    Structured record of a single decision protocol execution.
    Every DecisionEvent is forwarded to the DR-AIS immutable audit logger.
    No decision is made without a corresponding DecisionEvent being emitted.
    """
    timestamp_ns: int = Field(default_factory=time.time_ns)
    outcome: DecisionOutcome
    telemetry_timestamp_ns: Optional[int] = None
    guardrail_report: Optional[ACSTelemetryGuardrailReport] = None
    llm_analysis: Optional[LLMAnalysis] = None
    proposed_action: Optional[str] = None
    actuation_approved: bool = False
    requires_human_approval: bool = False
    human_approval_token: Optional[str] = None  # Future: cryptographic approval token
    message: str = ""

    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# Decision Router
# ---------------------------------------------------------------------------

class DecisionRouter:
    """
    Bimodal Decision Protocol Router.

    Orchestrates the complete evaluation cycle for each incoming telemetry frame:
      1. Deterministic structural constraint check (GuardrailEngine)
      2. Heuristic anomaly detection (ClaudeAnomalyDetector) — only if guardrails pass
      3. Second-pass constraint check on any LLM-proposed action
      4. Structured DecisionEvent emission for DR-AIS audit logging

    Args:
        llm_window_size (int): Number of telemetry frames accumulated before
                               dispatching to the LLM for pattern analysis.
                               Default: 20 frames (0.2s at 100Hz).
        anomaly_confidence_threshold (float): Minimum LLM confidence score required
                                              to classify an LLM response as an anomaly
                                              action. Below this threshold, CONTINUE_MONITORING.
        enable_llm (bool): If False, the LLM layer is disabled entirely. The router
                           operates in pure-deterministic guardrail-only mode.
    """

    # Type 2 recoverable actions that can be autonomously actuated
    TYPE_2_ACTIONS: frozenset[str] = frozenset({
        "CONTINUE_MONITORING",
        "INCREASE_SAMPLING_RATE",
        "SOFT_RESET_WHEEL_1",
        "SOFT_RESET_WHEEL_2",
        "SOFT_RESET_WHEEL_3",
    })

    # Type 1 irreversible actions requiring human cryptographic approval
    TYPE_1_ACTIONS: frozenset[str] = frozenset({
        "ALERT_OPERATOR_MARGINAL",
        "ALERT_OPERATOR_CRITICAL",
    })

    def __init__(
        self,
        llm_window_size: int = 20,
        anomaly_confidence_threshold: float = 0.65,
        enable_llm: bool = True,
    ) -> None:
        self.guardrail_engine = GuardrailEngine()
        self.claude = ClaudeAnomalyDetector() if enable_llm else None
        self.llm_window_size = llm_window_size
        self.anomaly_confidence_threshold = anomaly_confidence_threshold
        self._telemetry_window: deque[dict] = deque(maxlen=llm_window_size)

    def process(self, raw_telemetry_json: str) -> DecisionEvent:
        """
        Processes a single raw telemetry JSON frame through the full bimodal protocol.

        Args:
            raw_telemetry_json: Serialized JSON string from the ACS simulator.

        Returns:
            DecisionEvent: Full structured record of the decision outcome.
        """
        # --- Parse telemetry ---
        try:
            telemetry: dict = json.loads(raw_telemetry_json)
        except json.JSONDecodeError as e:
            logger.error("FATAL: Telemetry JSON parse failure: %s", e)
            return DecisionEvent(
                outcome=DecisionOutcome.GUARDRAIL_VIOLATION_FATAL,
                message=f"Telemetry deserialization failure: {e}",
                requires_human_approval=True,
            )

        telemetry_ts = telemetry.get("timestamp_ns")
        logger.debug("Processing telemetry frame ts=%d", telemetry_ts or 0)

        # ================================================================
        # STAGE 1: DETERMINISTIC STRUCTURAL CONSTRAINT CHECK
        # GuardrailEngine evaluates all SysML-derived Pydantic constraints.
        # This runs synchronously on every frame. Zero exceptions.
        # ================================================================
        report: ACSTelemetryGuardrailReport = self.guardrail_engine.evaluate(telemetry)

        if not report.passed:
            return self._handle_guardrail_violation(report, telemetry_ts)

        # ================================================================
        # STAGE 2: HEURISTIC ANOMALY DETECTION (LLM Layer)
        # Only reached if the telemetry frame passes all structural checks.
        # Accumulate a window; dispatch to Claude when full.
        # ================================================================
        self._telemetry_window.append(telemetry)

        if self.claude is None or len(self._telemetry_window) < self.llm_window_size:
            return DecisionEvent(
                outcome=DecisionOutcome.GUARDRAIL_PASS_LLM_SKIPPED,
                telemetry_timestamp_ns=telemetry_ts,
                guardrail_report=report,
                actuation_approved=False,
                message="Telemetry nominal. Accumulating LLM window.",
            )

        # Dispatch to Claude
        window_snapshot = list(self._telemetry_window)
        self._telemetry_window.clear()  # Reset window after dispatch

        try:
            analysis: LLMAnalysis = self.claude.analyze(window_snapshot)
        except RuntimeError as e:
            # Claude violated the tool_use contract: LLM Trust Boundary Violation
            logger.error("LLM TRUST BOUNDARY VIOLATION: %s", e)
            return DecisionEvent(
                outcome=DecisionOutcome.LLM_TRUST_BOUNDARY_VIOLATION,
                telemetry_timestamp_ns=telemetry_ts,
                guardrail_report=report,
                requires_human_approval=True,
                message=str(e),
            )

        # ================================================================
        # STAGE 3: SECOND-PASS GUARDRAIL ON LLM OUTPUT
        # Claude proposed an action. Route based on action type classification.
        # NOTE: Any proposed hardware state change would be re-validated here.
        # For this implementation, actions are classified as Type 1/2. Future
        # phases will validate proposed numeric parameter values against guardrails.
        # ================================================================
        if not analysis.anomaly_detected or analysis.confidence < self.anomaly_confidence_threshold:
            return DecisionEvent(
                outcome=DecisionOutcome.GUARDRAIL_PASS_LLM_NOMINAL,
                telemetry_timestamp_ns=telemetry_ts,
                guardrail_report=report,
                llm_analysis=analysis,
                proposed_action=analysis.recommended_action,
                actuation_approved=False,
                message=(
                    f"LLM: No actionable anomaly. "
                    f"confidence={analysis.confidence:.4f} < threshold={self.anomaly_confidence_threshold}"
                    if analysis.confidence < self.anomaly_confidence_threshold
                    else "LLM: Nominal telemetry confirmed."
                ),
            )

        # Anomaly confirmed by LLM — classify action type
        proposed = analysis.recommended_action

        if proposed in self.TYPE_2_ACTIONS:
            logger.warning(
                "LLM ANOMALY (Type 2): %s | action: %s | confidence: %.4f",
                analysis.affected_subsystem, proposed, analysis.confidence
            )
            return DecisionEvent(
                outcome=DecisionOutcome.GUARDRAIL_PASS_LLM_ANOMALY_TYPE2,
                telemetry_timestamp_ns=telemetry_ts,
                guardrail_report=report,
                llm_analysis=analysis,
                proposed_action=proposed,
                actuation_approved=True,  # Autonomous actuation approved
                requires_human_approval=False,
                message=(
                    f"LLM anomaly confirmed (Type 2 / Reversible). "
                    f"Autonomous actuation: {proposed}"
                ),
            )

        if proposed in self.TYPE_1_ACTIONS:
            logger.critical(
                "LLM ANOMALY (Type 1): %s | action: %s | confidence: %.4f — HUMAN APPROVAL REQUIRED",
                analysis.affected_subsystem, proposed, analysis.confidence
            )
            return DecisionEvent(
                outcome=DecisionOutcome.GUARDRAIL_PASS_LLM_ANOMALY_TYPE1,
                telemetry_timestamp_ns=telemetry_ts,
                guardrail_report=report,
                llm_analysis=analysis,
                proposed_action=proposed,
                actuation_approved=False,
                requires_human_approval=True,
                message=(
                    f"LLM anomaly confirmed (Type 1 / Irreversible). "
                    f"Human cryptographic approval required: {proposed}"
                ),
            )

        # Unknown action proposed by Claude — treat as trust boundary violation
        logger.error(
            "LLM proposed unknown action '%s' not in permitted action set.", proposed
        )
        return DecisionEvent(
            outcome=DecisionOutcome.LLM_TRUST_BOUNDARY_VIOLATION,
            telemetry_timestamp_ns=telemetry_ts,
            guardrail_report=report,
            llm_analysis=analysis,
            proposed_action=proposed,
            actuation_approved=False,
            requires_human_approval=True,
            message=(
                f"LLM proposed action '{proposed}' is outside the permitted "
                f"action enumeration. Routed to human review."
            ),
        )

    # ---------------------------------------------------------------------------
    # Internal: Guardrail Violation Handlers
    # ---------------------------------------------------------------------------

    def _handle_guardrail_violation(
        self, report: ACSTelemetryGuardrailReport, telemetry_ts: Optional[int]
    ) -> DecisionEvent:
        """
        Handles all structural constraint violations detected by the GuardrailEngine.
        LLM is NOT invoked. Decision is made deterministically based on severity.
        """
        # Log all violations
        for v in report.violations:
            logger.critical(
                "[GUARDRAIL VIOLATION] field=%s observed=%.3f limit=%.3f severity=%s action=%s | %s",
                v.field, v.observed_value, v.limit_value, v.severity, v.action_type, v.message
            )

        if report.has_fatal_violation:
            return DecisionEvent(
                outcome=DecisionOutcome.GUARDRAIL_VIOLATION_FATAL,
                telemetry_timestamp_ns=telemetry_ts,
                guardrail_report=report,
                actuation_approved=True,  # Safe-mode PID override is autonomously applied
                requires_human_approval=True,  # And human notified
                message=(
                    f"FATAL CONSTRAINT VIOLATION: {len(report.violations)} violation(s). "
                    f"LLM bypassed. Safe-mode PID fallback activated."
                ),
            )

        return DecisionEvent(
            outcome=DecisionOutcome.GUARDRAIL_VIOLATION_CRITICAL,
            telemetry_timestamp_ns=telemetry_ts,
            guardrail_report=report,
            actuation_approved=False,
            requires_human_approval=True,
            message=(
                f"CRITICAL CONSTRAINT VIOLATION: {len(report.violations)} violation(s). "
                f"LLM bypassed. Human operator alert dispatched."
            ),
        )
