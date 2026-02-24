"""
eval_harness/evaluator.py

Statistical Evaluation Harness for the SafeACS DR-AIS Audit Log.

Parses one or more DR-AIS JSONL log files and computes the KPIs defined in
Phase 1 (RTM.md, TASKS.md). Designed for offline batch analysis — run after
a completed simulation session to quantify the system's safety performance.

KPIs Computed:
  1. Constraint Adherence Rate (CAR): % of decisions where the system correctly
     enforced all SysML-derived hardware constraints. Must be 100%.
  2. Deterministic Guardrail Latency (DGL): p50/p95/p99 of the time taken by
     GuardrailEngine.evaluate() in microseconds.
  3. LLM Cognitive Inference Latency (CIL): p50/p95/p99 of Claude API round-trip
     latency in microseconds (LLM-dispatched frames only).
  4. Return on Cognitive Spend (RoCS): Ratio of actionable anomaly detections
     to total LLM token cost. Higher is better.
  5. LLM Trust Boundary Violation Rate: % of LLM interactions that violated
     the tool_use contract (safety-critical metric, must be 0%).

Standards: NIST AI RMF 1.0 MEASURE-2.5, RTM-010 (RoCS), RTM-011 (Latency)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import numpy as np

# ---------------------------------------------------------------------------
# ANSI color helpers for terminal output
# ---------------------------------------------------------------------------
_RED = "\033[91m"
_GRN = "\033[92m"
_YLW = "\033[93m"
_BLU = "\033[94m"
_CYN = "\033[96m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_RST = "\033[0m"

def _pass(v: str) -> str: return f"{_GRN}{_BOLD}{v}{_RST}"
def _fail(v: str) -> str: return f"{_RED}{_BOLD}{v}{_RST}"
def _warn(v: str) -> str: return f"{_YLW}{_BOLD}{v}{_RST}"
def _hdr(v: str) -> str:  return f"{_BLU}{_BOLD}{v}{_RST}"
def _dim(v: str) -> str:  return f"{_DIM}{v}{_RST}"


# ---------------------------------------------------------------------------
# Outcome classification helpers
# ---------------------------------------------------------------------------

GUARDRAIL_VIOLATION_OUTCOMES = {
    "GUARDRAIL_VIOLATION_FATAL",
    "GUARDRAIL_VIOLATION_CRITICAL",
}

LLM_DISPATCHED_OUTCOMES = {
    "GUARDRAIL_PASS_LLM_NOMINAL",
    "GUARDRAIL_PASS_LLM_ANOMALY_TYPE2",
    "GUARDRAIL_PASS_LLM_ANOMALY_TYPE1",
    "LLM_TRUST_BOUNDARY_VIOLATION",
}

ACTIONABLE_ANOMALY_OUTCOMES = {
    "GUARDRAIL_PASS_LLM_ANOMALY_TYPE2",
    "GUARDRAIL_PASS_LLM_ANOMALY_TYPE1",
}


# ---------------------------------------------------------------------------
# Log Parser
# ---------------------------------------------------------------------------

def load_records(log_paths: list[Path]) -> list[dict]:
    """
    Loads and parses all JSONL records from the provided log file paths.
    Skips malformed lines with a warning rather than crashing.
    """
    records = []
    for path in log_paths:
        if not path.exists():
            print(f"{_warn('WARNING')} Log file not found: {path}")
            continue
        with open(path, encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"{_warn('WARNING')} Skipping malformed record at {path}:{i}: {e}")
    return records


# ---------------------------------------------------------------------------
# KPI Computations
# ---------------------------------------------------------------------------

def _constraint_adherence_rate(records: list[dict]) -> tuple[float, int, int]:
    """
    Constraint Adherence Rate (CAR).

    Numerator: decisions where the system correctly enforced all hardware constraints
               (either passed cleanly, or detected and mitigated a violation).
    Denominator: all decisions.

    A TRUE CAR failure would be a case where a violation existed but the system
    did NOT flag it (false negative on a safety constraint). In this architecture,
    that is architecturally impossible — Pydantic raises on schema violations.
    This metric confirms that every fatal violation resulted in the correct outcome.
    """
    total = len(records)
    incorrect = 0
    for r in records:
        outcome = r.get("outcome", "")
        guardrail = r.get("guardrail", {})
        has_fatal = guardrail.get("has_fatal_violation", False)
        # A fatal violation that was actuation-approved without human approval = incorrect
        if has_fatal and r.get("actuation_approved") and not r.get("requires_human_approval"):
            incorrect += 1
    correct = total - incorrect
    rate = (correct / total * 100.0) if total > 0 else 0.0
    return rate, correct, total


def _latency_percentiles(values_us: list[float], label: str) -> dict:
    """Computes p50, p95, p99 for a list of latency values (microseconds)."""
    if not values_us:
        return {"label": label, "count": 0, "p50_us": None, "p95_us": None, "p99_us": None, "mean_us": None}
    arr = np.array(values_us)
    return {
        "label": label,
        "count": len(arr),
        "mean_us": float(np.mean(arr)),
        "p50_us": float(np.percentile(arr, 50)),
        "p95_us": float(np.percentile(arr, 95)),
        "p99_us": float(np.percentile(arr, 99)),
    }


def _rocs(records: list[dict]) -> dict:
    """
    Return on Cognitive Spend (RoCS).

    RoCS = (Actionable Anomaly Detections) / (Total LLM Tokens Consumed)

    A higher value means Claude is flagging more real anomalies per token spent.
    A RoCS of 0.0 means the LLM was invoked but produced no actionable detections.

    Unit: anomaly detections per 1,000 tokens (detections / kTokens)
    """
    actionable_anomalies = 0
    total_tokens = 0
    total_llm_calls = 0
    input_tokens_list = []
    output_tokens_list = []

    for r in records:
        rocs_t = r.get("rocs_telemetry")
        if rocs_t is None:
            continue
        total_llm_calls += 1
        inp = rocs_t.get("input_tokens") or 0
        out = rocs_t.get("output_tokens") or 0
        total_tokens += inp + out
        input_tokens_list.append(inp)
        output_tokens_list.append(out)

        if r.get("outcome") in ACTIONABLE_ANOMALY_OUTCOMES:
            actionable_anomalies += 1

    rocs_value = (actionable_anomalies / (total_tokens / 1000)) if total_tokens > 0 else 0.0

    return {
        "rocs_per_ktokens": rocs_value,
        "actionable_anomalies": actionable_anomalies,
        "total_llm_calls": total_llm_calls,
        "total_tokens": total_tokens,
        "mean_input_tokens": float(np.mean(input_tokens_list)) if input_tokens_list else 0.0,
        "mean_output_tokens": float(np.mean(output_tokens_list)) if output_tokens_list else 0.0,
    }


def _trust_boundary_violation_rate(records: list[dict]) -> tuple[float, int, int]:
    """LLM Trust Boundary Violation Rate. Must be 0% for system certification."""
    llm_calls = [r for r in records if r.get("outcome") in LLM_DISPATCHED_OUTCOMES]
    violations = [r for r in llm_calls if r.get("outcome") == "LLM_TRUST_BOUNDARY_VIOLATION"]
    rate = (len(violations) / len(llm_calls) * 100.0) if llm_calls else 0.0
    return rate, len(violations), len(llm_calls)


def _outcome_distribution(records: list[dict]) -> dict[str, int]:
    """Counts occurrences of each DecisionOutcome across all records."""
    dist: dict[str, int] = {}
    for r in records:
        outcome = r.get("outcome", "UNKNOWN")
        dist[outcome] = dist.get(outcome, 0) + 1
    return dict(sorted(dist.items(), key=lambda x: x[1], reverse=True))


# ---------------------------------------------------------------------------
# Terminal Report Renderer
# ---------------------------------------------------------------------------

def print_report(records: list[dict], log_paths: list[Path]) -> None:
    """Renders the full KPI evaluation report to stdout."""

    W = 70
    SEP = "─" * W
    DBL = "═" * W

    print(f"\n{_hdr(DBL)}")
    print(_hdr(f"{'SafeACS DR-AIS EVALUATION REPORT':^{W}}"))
    print(_hdr(DBL))
    print(_dim(f"  Sources: {', '.join(str(p) for p in log_paths)}"))
    print(_dim(f"  Total records analysed: {len(records)}"))
    print(f"{_hdr(SEP)}\n")

    if not records:
        print(f"  {_warn('No records found. Run a simulation session first.')}\n")
        return

    # -----------------------------------------------------------------------
    # 1. Outcome Distribution
    # -----------------------------------------------------------------------
    print(f"{_hdr('1. DECISION OUTCOME DISTRIBUTION')}")
    dist = _outcome_distribution(records)
    for outcome, count in dist.items():
        pct = count / len(records) * 100
        bar = "█" * int(pct / 2)
        color = _GRN if "PASS" in outcome else (_RED if ("FATAL" in outcome or "VIOLATION" in outcome) else _YLW)
        print(f"  {color}{outcome:<45}{_RST} {count:>5}  ({pct:5.1f}%)  {color}{bar}{_RST}")
    print()

    # -----------------------------------------------------------------------
    # 2. Constraint Adherence Rate
    # -----------------------------------------------------------------------
    print(f"{_hdr('2. CONSTRAINT ADHERENCE RATE  [Target: 100%]')}")
    car, correct, total = _constraint_adherence_rate(records)
    car_str = f"{car:.4f}%"
    status = _pass(f"PASS  {car_str}") if car == 100.0 else _fail(f"FAIL  {car_str}")
    print(f"  {status} ({correct}/{total} decisions correctly enforced)")
    print(_dim("  Definition: Every fatal hardware constraint violation was correctly"))
    print(_dim("  intercepted and routed to safe-mode / human approval."))
    print()

    # -----------------------------------------------------------------------
    # 3. Deterministic Guardrail Latency
    # -----------------------------------------------------------------------
    print(f"{_hdr('3. DETERMINISTIC GUARDRAIL LATENCY  [Synchronous / Edge]')}")
    guardrail_latencies = [
        r["guardrail"]["latency_us"]
        for r in records
        if r.get("guardrail", {}).get("latency_us") is not None
    ]
    gl = _latency_percentiles(guardrail_latencies, "GuardrailEngine.evaluate()")
    if gl["count"] > 0:
        p95_gl = f"{gl['p95_us']:,.1f} µs"
        print(f"  Samples  : {gl['count']:,}")
        print(f"  Mean     : {gl['mean_us']:,.1f} µs")
        print(f"  p50      : {gl['p50_us']:,.1f} µs")
        print(f"  p95      : {_warn(p95_gl)}")
        print(f"  p99      : {gl['p99_us']:,.1f} µs")
    else:
        print(f"  {_dim('No guardrail latency data available.')}")
    print()

    # -----------------------------------------------------------------------
    # 4. LLM Cognitive Inference Latency
    # -----------------------------------------------------------------------
    print(f"{_hdr('4. LLM COGNITIVE INFERENCE LATENCY  [Claude API / Cloud]')}")
    llm_latencies = [
        r["rocs_telemetry"]["llm_latency_us"]
        for r in records
        if r.get("rocs_telemetry") and r["rocs_telemetry"].get("llm_latency_us") is not None
    ]
    cl = _latency_percentiles(llm_latencies, "ClaudeAnomalyDetector.analyze()")
    if cl["count"] > 0:
        p95_cl = f"{cl['p95_us'] / 1_000:,.1f} ms"
        print(f"  Samples  : {cl['count']:,}")
        print(f"  Mean     : {cl['mean_us'] / 1_000:,.1f} ms")
        print(f"  p50      : {cl['p50_us'] / 1_000:,.1f} ms")
        print(f"  p95      : {_warn(p95_cl)}")
        print(f"  p99      : {cl['p99_us'] / 1_000:,.1f} ms")
    else:
        print(f"  {_dim('No LLM latency data (no LLM-dispatched frames in log).')}")
    print()

    # -----------------------------------------------------------------------
    # 5. Return on Cognitive Spend (RoCS)
    # -----------------------------------------------------------------------
    print(f"{_hdr('5. RETURN ON COGNITIVE SPEND (RoCS)')}")
    rocs = _rocs(records)
    if rocs["total_llm_calls"] > 0:
        rocs_val = rocs["rocs_per_ktokens"]
        rocs_color = _GRN if rocs_val > 0 else _YLW
        print(f"  RoCS                  : {rocs_color}{rocs_val:.4f} detections / kTokens{_RST}")
        print(f"  Actionable anomalies  : {rocs['actionable_anomalies']}")
        print(f"  Total LLM calls       : {rocs['total_llm_calls']}")
        print(f"  Total tokens consumed : {rocs['total_tokens']:,}")
        print(f"  Mean input tokens     : {rocs['mean_input_tokens']:.0f}")
        print(f"  Mean output tokens    : {rocs['mean_output_tokens']:.0f}")
        print(_dim("  RoCS = Actionable Anomaly Detections / (Total Tokens / 1000)"))
    else:
        print(f"  {_dim('No LLM calls in log. RoCS requires live Claude API session.')}")
    print()

    # -----------------------------------------------------------------------
    # 6. LLM Trust Boundary Violation Rate
    # -----------------------------------------------------------------------
    print(f"{_hdr('6. LLM TRUST BOUNDARY VIOLATION RATE  [Target: 0%]')}")
    tbvr, viols, llm_calls = _trust_boundary_violation_rate(records)
    tbvr_str = f"{tbvr:.4f}%"
    status = _pass(f"PASS  {tbvr_str}") if tbvr == 0.0 else _fail(f"FAIL  {tbvr_str}")
    if llm_calls > 0:
        print(f"  {status} ({viols} violations in {llm_calls} LLM interactions)")
    else:
        print(f"  {_dim('No LLM calls logged in this session.')}")
    print()

    print(f"{_hdr(DBL)}")
    print(_hdr(f"{'END OF REPORT':^{W}}"))
    print(f"{_hdr(DBL)}\n")


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main(log_paths: Optional[list[Path]] = None) -> None:
    """
    CLI entry point. Accepts log file paths as arguments, or defaults to
    scanning the `logs/dr_ais/` directory for all JSONL files.

    Usage:
        python -m eval_harness.evaluator
        python -m eval_harness.evaluator logs/dr_ais/dr_ais_session1.jsonl
    """
    if log_paths is None:
        args = sys.argv[1:]
        if args:
            log_paths = [Path(a) for a in args]
        else:
            default_dir = Path("logs/dr_ais")
            log_paths = sorted(default_dir.glob("*.jsonl")) if default_dir.exists() else []
            if not log_paths:
                print(f"\n{_warn('No log files found.')}")
                print(_dim("  Run a simulation session first, then re-run the evaluator."))
                print(_dim(f"  Default search path: {default_dir.resolve()}"))
                print(_dim("  Or pass log paths as arguments: python -m eval_harness.evaluator path/to/file.jsonl\n"))
                return

    records = load_records(log_paths)
    print_report(records, log_paths)


if __name__ == "__main__":
    main()
