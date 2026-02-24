"""
edge_node/dr_ais_logger.py

DR-AIS: Decision Records for AI Systems — Immutable Audit Logger.

Every DecisionEvent emitted by the DecisionRouter is captured here before
any actuation occurs. This log is the legal and forensic record of every
AI-assisted decision the system made, providing:

  1. Immutable chronological audit trail (JSONL format — append-only)
  2. Full RoCS (Return on Cognitive Spend) telemetry: token cost per decision
  3. Latency profiling: deterministic guardrail path vs. LLM inference path
  4. Anthropic API prompt hash for exact prompt reproducibility and audit

Architecture requirement: Logging MUST NOT introduce blocking I/O latency
to the primary hardware control loop. All disk writes are dispatched to a
dedicated background thread via a bounded queue. The control loop is never
stalled waiting for a filesystem operation.

Standards: DO-178C Section 11 (Software Life Cycle Data), NIST AI RMF 1.0 GOVERN-1.7
Traceability: RTM-009 (Audit Trail), RTM-010 (RoCS Measurement)
"""

from __future__ import annotations

import hashlib
import json
import logging
import queue
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from edge_node.decision_router import DecisionEvent, DecisionOutcome

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Log Record Schema
# Serialization format written to the JSONL audit ledger
# ---------------------------------------------------------------------------

def _build_log_record(
    event: DecisionEvent,
    guardrail_latency_us: float,
    llm_latency_us: Optional[float],
    prompt_hash: Optional[str],
    input_tokens: Optional[int],
    output_tokens: Optional[int],
) -> dict:
    """
    Constructs a structured log record from a DecisionEvent and its associated
    performance telemetry. This is the canonical DR-AIS record schema.

    All timestamps are UTC ISO-8601. All latencies are in microseconds (µs).
    Token counts are raw Anthropic API usage values.
    """
    violations = []
    if event.guardrail_report:
        for v in event.guardrail_report.violations:
            violations.append({
                "field": v.field,
                "observed_value": v.observed_value,
                "limit_value": v.limit_value,
                "severity": v.severity.value,
                "action_type": v.action_type.value,
                "message": v.message,
            })

    llm_record = None
    if event.llm_analysis:
        llm_record = {
            "anomaly_detected": event.llm_analysis.anomaly_detected,
            "confidence": event.llm_analysis.confidence,
            "recommended_action": event.llm_analysis.recommended_action,
            "affected_subsystem": event.llm_analysis.affected_subsystem,
            "reasoning": event.llm_analysis.reasoning,
        }

    # RoCS = actionable anomaly detections / total token cost
    # A single record cannot compute RoCS; evaluator.py aggregates across the log.
    rocs_telemetry = None
    if input_tokens is not None:
        rocs_telemetry = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": (input_tokens or 0) + (output_tokens or 0),
            "prompt_hash_sha256": prompt_hash,
            "llm_latency_us": llm_latency_us,
        }

    return {
        "schema_version": "1.0.0",
        "logged_at_utc": datetime.now(timezone.utc).isoformat(),
        "decision_timestamp_ns": event.timestamp_ns,
        "telemetry_timestamp_ns": event.telemetry_timestamp_ns,
        "outcome": event.outcome.value,
        "actuation_approved": event.actuation_approved,
        "requires_human_approval": event.requires_human_approval,
        "message": event.message,
        "guardrail": {
            "passed": event.guardrail_report.passed if event.guardrail_report else True,
            "has_fatal_violation": event.guardrail_report.has_fatal_violation if event.guardrail_report else False,
            "violation_count": len(violations),
            "violations": violations,
            "latency_us": guardrail_latency_us,
        },
        "llm": llm_record,
        "rocs_telemetry": rocs_telemetry,
    }


# ---------------------------------------------------------------------------
# DR-AIS Logger
# ---------------------------------------------------------------------------

class DRAISLogger:
    """
    Immutable Append-Only Audit Logger for the SafeACS Decision Router.

    Writes structured JSONL records to disk on a dedicated background thread,
    ensuring the primary hardware control loop is never blocked by I/O.

    Each record is one JSON object on one line — the JSONL format is designed
    for streaming ingestion, forensic audit, and offline statistical analysis.

    Usage:
        logger = DRAISLogger(log_dir=Path("logs/"))
        logger.start()

        # In the control loop — non-blocking
        logger.log(event, guardrail_latency_us=42.3)

        logger.stop()  # Flushes all pending records before shutdown

    Args:
        log_dir: Directory for JSONL audit files. Created if absent.
        max_queue_size: Max unwritten records before backpressure. Default: 10,000.
        session_tag: Optional string tag embedded in the log filename for experiment labeling.
    """

    def __init__(
        self,
        log_dir: Path = Path("logs/dr_ais"),
        max_queue_size: int = 10_000,
        session_tag: Optional[str] = None,
    ) -> None:
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)

        tag = f"_{session_tag}" if session_tag else ""
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.log_path = self.log_dir / f"dr_ais{tag}_{ts}.jsonl"

        self._queue: queue.Queue[Optional[dict]] = queue.Queue(maxsize=max_queue_size)
        self._worker = threading.Thread(target=self._write_worker, daemon=True, name="DRAISLogWorker")
        self._running = False

        # Per-session counters (for live status display)
        self.records_written: int = 0
        self.records_dropped: int = 0

        logger.info("DR-AIS Logger initialized. Log path: %s", self.log_path)

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    def start(self) -> None:
        """Starts the background write worker thread."""
        self._running = True
        self._worker.start()
        logger.info("DR-AIS Logger started (background thread active).")

    def stop(self, timeout_s: float = 5.0) -> None:
        """
        Gracefully shuts down the logger. Flushes all queued records before
        closing the log file. Blocks for up to `timeout_s` seconds.
        """
        logger.info("DR-AIS Logger shutdown requested. Flushing queue...")
        self._queue.put(None)  # Sentinel: signals worker to drain and exit
        self._worker.join(timeout=timeout_s)
        logger.info(
            "DR-AIS Logger stopped. Records written: %d | Dropped: %d",
            self.records_written, self.records_dropped
        )

    # -----------------------------------------------------------------------
    # Public API: Non-blocking log submission
    # -----------------------------------------------------------------------

    def log(
        self,
        event: DecisionEvent,
        guardrail_latency_us: float,
        llm_latency_us: Optional[float] = None,
        prompt_text: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
    ) -> None:
        """
        Enqueues a DecisionEvent for asynchronous serialization.

        This method returns immediately — it NEVER blocks the caller.
        If the queue is full (backpressure scenario), the record is dropped
        and counted in `self.records_dropped`. This is an acceptable
        trade-off: primary control loop safety is never sacrificed for logging.

        Args:
            event: The DecisionEvent from the DecisionRouter.
            guardrail_latency_us: Time taken by GuardrailEngine.evaluate() in microseconds.
            llm_latency_us: Time taken by ClaudeAnomalyDetector.analyze() in microseconds.
            prompt_text: The full prompt string sent to Claude (for SHA-256 hashing).
            input_tokens: Anthropic API input token count (from response.usage).
            output_tokens: Anthropic API output token count (from response.usage).
        """
        prompt_hash: Optional[str] = None
        if prompt_text:
            prompt_hash = hashlib.sha256(prompt_text.encode()).hexdigest()

        record = _build_log_record(
            event=event,
            guardrail_latency_us=guardrail_latency_us,
            llm_latency_us=llm_latency_us,
            prompt_hash=prompt_hash,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        try:
            self._queue.put_nowait(record)
        except queue.Full:
            self.records_dropped += 1
            logger.warning(
                "DR-AIS queue full — record dropped. Total dropped: %d. "
                "Consider increasing max_queue_size.",
                self.records_dropped
            )

    # -----------------------------------------------------------------------
    # Background Writer Thread
    # -----------------------------------------------------------------------

    def _write_worker(self) -> None:
        """
        Background thread: drains the queue and appends records to the JSONL file.
        Runs until a None sentinel is received, then flushes and exits.
        """
        with open(self.log_path, "a", encoding="utf-8", buffering=1) as f:
            while True:
                try:
                    record = self._queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                if record is None:
                    # Drain remaining items before exit
                    while not self._queue.empty():
                        try:
                            remaining = self._queue.get_nowait()
                            if remaining is not None:
                                f.write(json.dumps(remaining) + "\n")
                                self.records_written += 1
                        except queue.Empty:
                            break
                    break

                f.write(json.dumps(record) + "\n")
                self.records_written += 1
