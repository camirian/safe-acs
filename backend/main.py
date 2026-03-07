"""
backend/main.py

FastAPI Backend for SafeACS Mission Control.
Runs the Kinetic-Twin simulator in a background thread and exposes
REST/WebSocket endpoints for the React frontend.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from collections import deque
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from sim_engine.acs_simulator import ACSSimulator
from edge_node.decision_router import DecisionRouter, DecisionEvent, DecisionOutcome
from edge_node.dr_ais_logger import _build_log_record

# ---------------------------------------------------------------------------
# Setup & Globals
# ---------------------------------------------------------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("safeacs.api")

app = FastAPI(title="SafeACS API")

# Allow CORS for local React dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State (Thread-safe-ish via GIL and basic locks)
class AppState:
    def __init__(self) -> None:
        self.sim: ACSSimulator | None = None
        self.router: DecisionRouter | None = None
        self.sim_thread: threading.Thread | None = None
        self.is_running: bool = False
        
        # Telemetry Buffers for Front-end Polling
        self.history_rpms: deque[dict[str, Any]] = deque(maxlen=200)
        self.history_events: deque[dict[str, Any]] = deque(maxlen=50)
        
        # Fault Injection Flags
        self.inject_fatal: bool = False
        self.inject_drift: bool = False
        self.latest_llm_analysis: dict[str, Any] | None = None
        self.latest_sysml_state: str = "Nominal"
        
        self.lock = threading.Lock()

state = AppState()


# ---------------------------------------------------------------------------
# Background Simulation Loop
# ---------------------------------------------------------------------------

def _sim_worker() -> None:
    logger.info("Simulation thread started.")
    t_start = time.time()
    
    while state.is_running:
        loop_start = time.perf_counter()
        
        with state.lock:
            if not state.sim or not state.router:
                break
                
            # 1. Apply Fault Injections
            if state.inject_fatal:
                state.sim.rw_rpms.wheel_2 = 6500.0
                state.inject_fatal = False  # Let the simulator auto-recover naturally
            elif state.inject_drift:
                state.sim.inject_anomaly(wheel_index=3, drift_rate_rpm=100.0)
            else:
                state.sim.clear_anomaly()
                if state.sim.rw_rpms.wheel_2 > 6000:
                    state.sim.rw_rpms.wheel_2 = 2000.0

            # 2. Step Kinetic-Twin
            raw_telemetry = state.sim.run_step()
            raw_dict = json.loads(raw_telemetry)
            state.latest_sysml_state = raw_dict.get("sysml_state", "Nominal")
            
            # 3. Route through Bimodal Protocol
            t0 = time.perf_counter()
            event = state.router.process(raw_telemetry)
            guardrail_us = (time.perf_counter() - t0) * 1_000_000
            
            # 4. Mock DR-AIS Record for UI
            record = _build_log_record(
                event=event,
                guardrail_latency_us=guardrail_us,
                llm_latency_us=guardrail_us if event.llm_analysis else None,
                prompt_hash="live_demo_hash",
                input_tokens=420 if event.llm_analysis else 0,
                output_tokens=150 if event.llm_analysis else 0
            )
            
            # 5. Buffer outputs for React
            uptime = time.time() - t_start
            state.history_rpms.append({
                "time": round(uptime, 2),
                "W1": raw_dict["rw_rpms"]["wheel_1"],
                "W2": raw_dict["rw_rpms"]["wheel_2"],
                "W3": raw_dict["rw_rpms"]["wheel_3"]
            })
            state.history_events.append(record)
            
            if event.llm_analysis:
                state.latest_llm_analysis = event.llm_analysis.model_dump()
        
        # Sleep to maintain frequency (e.g. 5Hz for UI)
        elapsed = time.perf_counter() - loop_start
        sleep_time = max(0.0, 0.2 - elapsed)
        time.sleep(sleep_time)

    logger.info("Simulation thread stopped.")


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup_event() -> None:
    has_llm = bool(os.environ.get("ANTHROPIC_API_KEY"))
    logger.info(f"Starting SafeACS Backend. LLM Enabled: {has_llm}")
    
    state.sim = ACSSimulator(frequency_hz=5.0)
    state.router = DecisionRouter(
        enable_llm=has_llm,
        llm_window_size=15,
        anomaly_confidence_threshold=0.60
    )
    state.is_running = True
    
    state.sim_thread = threading.Thread(target=_sim_worker, daemon=True)
    state.sim_thread.start()

@app.on_event("shutdown")
def shutdown_event() -> None:
    state.is_running = False
    if state.sim_thread:
        state.sim_thread.join(timeout=2.0)


# ---------------------------------------------------------------------------
# REST Endpoints
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/api/state")
def get_state() -> dict[str, Any]:
    """Returns the current buffered state to the React frontend."""
    with state.lock:
        return {
            "has_llm": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "rpms": list(state.history_rpms),
            "latest_event": state.history_events[-1] if state.history_events else None,
            "dr_ais_ledger": list(state.history_events)[-10:], # Last 10
            "llm_analysis": state.latest_llm_analysis,
            "sysml_state": state.latest_sysml_state,
            "injections": {
                "fatal": state.inject_fatal,
                "drift": state.inject_drift
            }
        }

class InjectRequest(BaseModel):
    type: str  # "fatal", "drift", "clear"

@app.post("/api/inject")
def inject_fault(req: InjectRequest) -> dict[str, str]:
    with state.lock:
        if req.type == "fatal":
            state.inject_fatal = True
            state.inject_drift = False
        elif req.type == "drift":
            state.inject_drift = True
            state.inject_fatal = False
        elif req.type == "clear":
            state.inject_fatal = False
            state.inject_drift = False
            state.latest_llm_analysis = None
        else:
            raise HTTPException(status_code=400, detail="Invalid injection type")
            
    return {"status": f"Injected {req.type}"}

@app.post("/api/override")
def cryptographic_override() -> dict[str, str]:
    """Mock endpoint for the human operator approving a Type 1 Action."""
    with state.lock:
        state.latest_llm_analysis = None
        # In a real system, this would sign a JWT and unblock the actuation queue
    return {"status": "Override Authorized"}
