"""
Phase 3 Integration Verification Script.
Verifies GuardrailEngine and DecisionRouter logic without invoking the LLM.
"""
import json
import sys
from edge_node.guardrails import GuardrailEngine, ViolationSeverity
from edge_node.decision_router import DecisionRouter, DecisionOutcome

engine = GuardrailEngine()

NOMINAL = {
    "timestamp_ns": 1000000,
    "attitude_q": {"w": 1.0, "x": 0.0, "y": 0.0, "z": 0.0},
    "angular_rates": {"roll": 0.0, "pitch": 0.0, "yaw": 0.0},
    "rw_rpms": {"wheel_1": 2000.0, "wheel_2": 2000.0, "wheel_3": 2000.0}
}

results = []

def test(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    results.append((status, name))
    print(f"[{status}] {name}" + (f" | {detail}" if detail else ""))
    if not condition:
        sys.exit(1)

# 1. Nominal telemetry passes all guardrails
r = engine.evaluate(NOMINAL)
test("Guardrail: Nominal telemetry passes", r.passed, f"violations={len(r.violations)}")

# 2. Fatal RPM violation caught
fatal_rpm = {**NOMINAL, "rw_rpms": {"wheel_1": 2000.0, "wheel_2": 7500.0, "wheel_3": 2000.0}}
r2 = engine.evaluate(fatal_rpm)
test("Guardrail: Fatal RPM violation detected", not r2.passed and r2.has_fatal_violation,
     f"severity={r2.violations[0].severity}")

# 3. Angular rate violation caught
fatal_rate = {**NOMINAL, "angular_rates": {"roll": 8.0, "pitch": 0.0, "yaw": 0.0}}
r3 = engine.evaluate(fatal_rate)
test("Guardrail: Angular rate violation detected", not r3.passed, f"violations={len(r3.violations)}")

# 4. Quaternion corruption caught
bad_q = {**NOMINAL, "attitude_q": {"w": 2.0, "x": 2.0, "y": 2.0, "z": 2.0}}
r4 = engine.evaluate(bad_q)
test("Guardrail: Quaternion norm violation detected", not r4.passed)

# 5. DecisionRouter nominal outcome
router = DecisionRouter(enable_llm=False, llm_window_size=3)
e1 = router.process(json.dumps(NOMINAL))
test("Router: Nominal returns GUARDRAIL_PASS_LLM_SKIPPED",
     e1.outcome == DecisionOutcome.GUARDRAIL_PASS_LLM_SKIPPED)

# 6. DecisionRouter fatal violation bypasses LLM
e2 = router.process(json.dumps(fatal_rpm))
test("Router: Fatal RPM returns GUARDRAIL_VIOLATION_FATAL",
     e2.outcome == DecisionOutcome.GUARDRAIL_VIOLATION_FATAL and e2.requires_human_approval,
     f"requires_human={e2.requires_human_approval}")

# 7. LLMAnalysis Pydantic schema validation
from edge_node.claude_client import LLMAnalysis
llm = LLMAnalysis(
    anomaly_detected=True,
    confidence=0.87,
    recommended_action="SOFT_RESET_WHEEL_2",
    reasoning="Monotonic RPM drift on Wheel 2 over last 20 frames.",
    affected_subsystem="ReactionWheel_2"
)
test("LLMAnalysis: Pydantic schema validates correctly", llm.anomaly_detected and llm.confidence == 0.87)

print("\n=====================================")
print(f"PHASE 3 VERIFICATION: {sum(1 for s,_ in results if s=='PASS')}/{len(results)} TESTS PASSED")
print("=====================================")
