"""
ui/app.py

Streamlit Human-in-the-Loop Dashboard for SafeACS.
Deploys as a live, interactive container on Google Cloud Run.

Features:
- Live synthetic telemetry visualization (Kinetic-Twin)
- Deterministic Guardrail status indicators
- Anthropic Claude heuristic anomaly surfacing
- Cryptographic-style Type 1 Action approval mock UI
- DR-AIS live audit log
"""

import os
import time
import json
import threading
from collections import deque
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from sim_engine.acs_simulator import ACSSimulator
from edge_node.decision_router import DecisionRouter, DecisionEvent, DecisionOutcome
from edge_node.dr_ais_logger import _build_log_record

# ---------------------------------------------------------------------------
# Streamlit Config & Aesthetics
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="SafeACS | AI Assurance",
    page_icon="🛰️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for a deep-tech, aerospace feel
st.markdown("""
<style>
    .stApp {
        background-color: #0e1117;
    }
    .metric-box {
        background-color: #1e2127;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #333;
        text-align: center;
    }
    .violation-fatal {
        border-left: 4px solid #ff4b4b;
        background-color: rgba(255, 75, 75, 0.1);
        padding: 10px;
        margin-bottom: 10px;
        border-radius: 0 4px 4px 0;
    }
    .llm-anomaly {
        border-left: 4px solid #faca2b;
        background-color: rgba(250, 202, 43, 0.1);
        padding: 10px;
        margin-bottom: 10px;
        border-radius: 0 4px 4px 0;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Background Simulation Thread
# ---------------------------------------------------------------------------
def _run_simulation_thread():
    """Runs the ACS simulation loop independently of Streamlit UI refreshes."""
    sim = st.session_state.sim_engine
    router = st.session_state.decision_router
    
    while st.session_state.sim_running:
        t0 = time.perf_counter()
        
        # Apply UI-commanded injections
        with st.session_state.sim_lock:
            if st.session_state.inject_fatal:
                sim.rw_rpms.wheel_2 = 6500.0  # Force structural failure
            elif st.session_state.inject_drift:
                sim.inject_anomaly(wheel_index=3, drift_rate_rpm=100.0)
            else:
                sim.clear_anomaly()
                # If we just cleared fatal, reset back to nominal bounds
                if sim.rw_rpms.wheel_2 > 6000:
                    sim.rw_rpms.wheel_2 = 2000.0

            raw_telemetry = sim.run_step()
            raw_dict = json.loads(raw_telemetry)
            
            # Step the router
            event = router.process(raw_telemetry)
            guardrail_us = (time.perf_counter() - t0) * 1_000_000
            
            # Prepare DR-AIS record
            record = _build_log_record(
                event=event,
                guardrail_latency_us=guardrail_us,
                llm_latency_us=guardrail_us if event.llm_analysis else None,
                prompt_hash="live_demo_hash",
                input_tokens=420 if event.llm_analysis else 0,
                output_tokens=150 if event.llm_analysis else 0
            )
            
            # Append safely to UI buffers
            st.session_state.history_rpms.append({
                "time": time.time(),
                "W1": raw_dict["rw_rpms"]["wheel_1"],
                "W2": raw_dict["rw_rpms"]["wheel_2"],
                "W3": raw_dict["rw_rpms"]["wheel_3"]
            })
            st.session_state.history_events.append(record)
            
            if event.llm_analysis:
                st.session_state.latest_llm_analysis = event.llm_analysis

        time.sleep(sim.dt)

def _init_state():
    if "sim_running" not in st.session_state:
        # Check API Key availability
        has_llm = bool(os.environ.get("ANTHROPIC_API_KEY"))
        
        st.session_state.sim_running = True
        st.session_state.sim_engine = ACSSimulator(frequency_hz=5.0)  # Slower for UI
        st.session_state.decision_router = DecisionRouter(
            enable_llm=has_llm, 
            llm_window_size=15, 
            anomaly_confidence_threshold=0.60
        )
        st.session_state.sim_lock = threading.Lock()
        
        st.session_state.history_rpms = deque(maxlen=100)
        st.session_state.history_events = deque(maxlen=50)
        st.session_state.inject_fatal = False
        st.session_state.inject_drift = False
        st.session_state.latest_llm_analysis = None
        st.session_state.has_llm = has_llm
        
        # Start background worker
        threading.Thread(target=_run_simulation_thread, daemon=True).start()

_init_state()


# ---------------------------------------------------------------------------
# UI Layout
# ---------------------------------------------------------------------------
st.title("🛰️ SafeACS Mission Control")
st.markdown("*Cyber-Physical AI Assurance Framework — Bimodal Protocol Demo*")

if not st.session_state.has_llm:
    st.warning("⚠️ No `ANTHROPIC_API_KEY` found. Operating in Deterministic Guardrail-Only mode.")

col_main, col_side = st.columns([3, 1])

with col_side:
    st.header("Fault Injection")
    st.caption("Manipulate the Kinetic-Twin Simulator")
    
    # Injection Controls
    if st.button("🚨 Inject Fatal Fault (W2 > 6000 RPM)", use_container_width=True):
        st.session_state.inject_fatal = True
        st.session_state.inject_drift = False
        
    if st.button("⚠️ Inject LLM Anomaly (W3 Drift)", use_container_width=True):
        st.session_state.inject_drift = True
        st.session_state.inject_fatal = False
        
    if st.button("✅ Clear All Faults (Nominal)", use_container_width=True, type="primary"):
        st.session_state.inject_fatal = False
        st.session_state.inject_drift = False
        st.session_state.latest_llm_analysis = None

    st.markdown("---")
    st.header("System Architecture")
    st.markdown("""
    **Layer 1: Deterministic**
    - SysML v2 derived Pydantic boundaries.
    - `±6000 RPM` hard structural limit.
    - Synchronous evaluation < 1ms.
    
    **Layer 2: Heuristic (Claude)**
    - Read-only cognitive observer.
    - Evaluates telemetry windows.
    - Predicts emergent failures (Drift).
    """)


with col_main:
    # ----------------------------------------------------------
    # Telemetry Visualization
    # ----------------------------------------------------------
    st.subheader("Reaction Wheel Telemetry (RPM)")
    
    with st.session_state.sim_lock:
        df_rpms = pd.DataFrame(list(st.session_state.history_rpms))
        
    if not df_rpms.empty:
        # Plotly chart for strict limit lines
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_rpms['time'], y=df_rpms['W1'], name="Wheel 1", line=dict(color='#00CC96')))
        fig.add_trace(go.Scatter(x=df_rpms['time'], y=df_rpms['W2'], name="Wheel 2", line=dict(color='#EF553B')))
        fig.add_trace(go.Scatter(x=df_rpms['time'], y=df_rpms['W3'], name="Wheel 3", line=dict(color='#AB63FA')))
        
        # Add guardrail bounds
        fig.add_hline(y=6000, line_dash="dash", line_color="red", annotation_text="Guardrail (+6000)")
        fig.add_hline(y=-6000, line_dash="dash", line_color="red", annotation_text="Guardrail (-6000)")
        
        fig.update_layout(
            height=300, 
            margin=dict(l=0, r=0, t=10, b=0),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showticklabels=False, title="Time"),
            yaxis=dict(title="RPM", range=[0, 7000])
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # ----------------------------------------------------------
    # Guardrail & LLM Interception Events
    # ----------------------------------------------------------
    col_edge, col_cloud = st.columns(2)
    
    with st.session_state.sim_lock:
        latest_event = st.session_state.history_events[-1] if st.session_state.history_events else None
        llm = st.session_state.latest_llm_analysis
        
    with col_edge:
        st.subheader("🛡️ Edge Guardrail")
        if latest_event:
            fatal = latest_event["guardrail"].get("has_fatal_violation", False)
            if fatal:
                st.markdown("<div class='violation-fatal'>", unsafe_allow_html=True)
                st.error("FATAL VIOLATION: Structural limit exceeded.")
                st.write(f"**Outcome:** {latest_event['outcome']}")
                for v in latest_event["guardrail"]["violations"]:
                    st.write(f"- {v['field']} | {v['message']}")
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.success(f"NOMINAL | Latency: {latest_event['guardrail']['latency_us']:.1f} µs")

    with col_cloud:
        st.subheader("🧠 Claude Cognitive Layer")
        if llm:
            if llm.anomaly_detected:
                st.markdown("<div class='llm-anomaly'>", unsafe_allow_html=True)
                st.warning(f"HEURISTIC ANOMALY DETECTED | Confidence: {llm.confidence:.2f}")
                st.write(f"**Reasoning:** {llm.reasoning}")
                st.write(f"**Action:** `{llm.recommended_action}`")
                
                # Human-in-the-loop Mock UI
                if "TYPE_1" in latest_event.get("outcome", ""):
                    if st.button("🔐 Cryptographic Override (Approve Action)"):
                        st.success("Action Authorised by Operator.")
                        st.session_state.latest_llm_analysis = None
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.info("Nominal pattern confirmed. No anomalies.")
        else:
            st.info("Accumulating telemetry window..." if st.session_state.has_llm else "LLM Observer Disabled.")

    st.markdown("---")
    
    # ----------------------------------------------------------
    # Immutable Audit Log
    # ----------------------------------------------------------
    st.subheader("DR-AIS Immutable Ledger")
    st.caption("Live JSONL Audit Stream")
    
    with st.session_state.sim_lock:
        df_events = pd.DataFrame(list(st.session_state.history_events)).tail(10)
        
    if not df_events.empty:
        # Simplify display
        display_df = df_events[["logged_at_utc", "outcome", "actuation_approved", "requires_human_approval"]].copy()
        st.dataframe(display_df, use_container_width=True, hide_index=True)


# Auto-refresh loop
time.sleep(1.0)
st.rerun()
