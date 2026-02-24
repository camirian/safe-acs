"""
run_simulation.py

Full Integration Simulation Script for SafeACS Phase 4 Verification.

Orchestrates a complete end-to-end session:
  1. Initialises the ACS simulator (Kinetic Twin)
  2. Starts the DR-AIS audit logger (background thread)
  3. Runs nominal telemetry through the Decision Router
  4. Injects an RPM fault (triggers GUARDRAIL_VIOLATION_FATAL)
  5. Clears fault; injects a subtle drift anomaly (triggers LLM if enabled)
  6. Stops the logger and flushes all records to JSONL
  7. Automatically invokes the Evaluation Harness on the generated log

Usage:
    python run_simulation.py                 # Guardrail-only (offline, no API key)
    ANTHROPIC_API_KEY=sk-... python run_simulation.py --llm  # Full LLM pipeline
"""

import argparse
import logging
import time
from pathlib import Path

from sim_engine.acs_simulator import ACSSimulator
from edge_node.decision_router import DecisionRouter, DecisionOutcome
from edge_node.dr_ais_logger import DRAISLogger
from eval_harness.evaluator import main as run_evaluation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
)
logger = logging.getLogger("run_simulation")

_SEP = "─" * 60


def run(enable_llm: bool = False, window_size: int = 10) -> Path:
    """
    Executes a complete simulation session and returns the path to the
    generated DR-AIS JSONL log file.
    """
    session_tag = "llm" if enable_llm else "guardrail_only"

    sim = ACSSimulator(frequency_hz=10.0)
    router = DecisionRouter(
        enable_llm=enable_llm,
        llm_window_size=window_size,
        anomaly_confidence_threshold=0.60,
    )
    audit_logger = DRAISLogger(
        log_dir=Path("logs/dr_ais"),
        session_tag=session_tag,
    )
    audit_logger.start()

    def process_tick(label: str = "") -> DecisionOutcome:
        """Run one simulation tick through the full instrumented pipeline."""
        import time as _time

        # --- Deterministic guardrail pass (timed) ---
        t0 = _time.perf_counter()
        raw_json = sim.run_step()
        event = router.process(raw_json)
        guardrail_us = (_time.perf_counter() - t0) * 1_000_000

        # LLM latency is not separately measurable here without refactoring the router,
        # so we approximate from the total tick time minus guardrail overhead when LLM fired.
        # In Phase 5, the router will expose these directly via instrumented return values.
        llm_latency_us = None
        if event.llm_analysis is not None:
            llm_latency_us = guardrail_us  # Placeholder; full instrumentation in Phase 5

        audit_logger.log(
            event=event,
            guardrail_latency_us=guardrail_us,
            llm_latency_us=llm_latency_us,
        )

        tag = f"[{label}] " if label else ""
        if event.outcome in (
            DecisionOutcome.GUARDRAIL_VIOLATION_FATAL,
            DecisionOutcome.GUARDRAIL_VIOLATION_CRITICAL,
            DecisionOutcome.LLM_TRUST_BOUNDARY_VIOLATION,
        ):
            logger.warning("%s%s | %s", tag, event.outcome.value, event.message[:80])
        elif event.llm_analysis:
            logger.info(
                "%sLLM: anomaly=%s confidence=%.2f action=%s",
                tag,
                event.llm_analysis.anomaly_detected,
                event.llm_analysis.confidence,
                event.llm_analysis.recommended_action,
            )
        else:
            logger.debug("%s%s", tag, event.outcome.value)

        return event.outcome

    # =========================================================================
    # PHASE A: Nominal operation (20 ticks)
    # =========================================================================
    print(f"\n{_SEP}")
    print("  PHASE A: NOMINAL TELEMETRY (20 ticks @ 10Hz)")
    print(_SEP)
    for i in range(20):
        process_tick(label="NOMINAL")
        time.sleep(sim.dt)

    # =========================================================================
    # PHASE B: Inject a fatal RPM fault (5 ticks)
    # Directly sets wheel RPM above structural limit to trigger FATAL guardrail
    # =========================================================================
    print(f"\n{_SEP}")
    print("  PHASE B: FATAL RPM FAULT — Wheel 2 → 6500 RPM")
    print(_SEP)
    sim.rw_rpms.wheel_2 = 6500.0  # Force above ±6000 structural limit
    for i in range(5):
        process_tick(label="FATAL_RPM")
        time.sleep(sim.dt)
    sim.rw_rpms.wheel_2 = 2000.0  # Restore wheel to nominal

    # =========================================================================
    # PHASE C: Subtle drift anomaly injection (LLM detection scenario)
    # Drift is slow enough to NOT trigger guardrails immediately,
    # but accumulates across frames — LLM should surface it
    # =========================================================================
    print(f"\n{_SEP}")
    print(f"  PHASE C: DRIFT ANOMALY on Wheel 3 (50 RPM/s) — {'LLM active' if enable_llm else 'LLM disabled (guardrail-only)'}")
    print(_SEP)
    sim.inject_anomaly(wheel_index=3, drift_rate_rpm=50.0)
    tick_count = window_size + 5 if enable_llm else 15
    for i in range(tick_count):
        process_tick(label="DRIFT")
        time.sleep(sim.dt)
    sim.clear_anomaly()

    # =========================================================================
    # PHASE D: Return to nominal (10 ticks)
    # =========================================================================
    print(f"\n{_SEP}")
    print("  PHASE D: RECOVERY — Return to nominal")
    print(_SEP)
    sim.rw_rpms.wheel_3 = 2000.0  # Hard reset after drift
    for i in range(10):
        process_tick(label="RECOVERY")
        time.sleep(sim.dt)

    # Flush and close
    audit_logger.stop()
    log_path = audit_logger.log_path
    logger.info("Simulation complete. DR-AIS log: %s (%d records written)", log_path, audit_logger.records_written)
    return log_path


def main() -> None:
    parser = argparse.ArgumentParser(description="SafeACS Phase 4 Simulation + Evaluation")
    parser.add_argument("--llm", action="store_true", help="Enable Claude LLM layer (requires ANTHROPIC_API_KEY)")
    parser.add_argument("--window", type=int, default=10, help="LLM telemetry window size (default: 10)")
    args = parser.parse_args()

    print(f"\n{'═' * 60}")
    print(f"  SafeACS — Phase 4 Simulation Session")
    print(f"  Mode: {'Full LLM Pipeline' if args.llm else 'Guardrail-Only (Offline)'}")
    print(f"{'═' * 60}")

    log_path = run(enable_llm=args.llm, window_size=args.window)

    print(f"\n{'═' * 60}")
    print(f"  Running Evaluation Harness on: {log_path}")
    print(f"{'═' * 60}")
    run_evaluation(log_paths=[log_path])


if __name__ == "__main__":
    main()
