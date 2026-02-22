# Workspace Scaffold Summary

## Directory Structure
```text
safe-acs/
├── docs/                # MBSE artifacts, RTM, Risk Register, C4 diagrams
├── edge_node/           # Jetson Orin Nano edge execution layer (deterministic guardrails)
├── sim_engine/          # Synthetic ACS telemetry generator (3-axis stabilization)
├── eval_harness/        # Boundary testing, DR-AIS auditing, RoCS metric generation
├── ui/                  # Streamlit dashboard for humans-in-the-loop and verification
├── tests/               # Pytest suite, property-based tests, boundary injection
├── .gitignore           # Environment exclusions
├── ARCHITECTURE.md      # Core framework definition
├── HAZARDS.md           # System hazards and mitigations
├── RTM.md               # Requirements traceability
└── TASKS.md             # Phase execution plan
```

## `.gitignore`
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.env
.venv/
venv/

# Streamlit
.streamlit/

# NVIDIA Jetson / Edge Compute
*.engine
*.plan
*.trt
.nv/

# Anthropic / Evaluations
anthropic_logs/
eval_results/

# IDE / OS
.vscode/
.idea/
.DS_Store
```
