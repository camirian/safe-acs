import { useState, useEffect, useRef } from 'react';
import { Shield, Satellite, Github, Circle } from 'lucide-react';
import { TelemetryChart } from './components/TelemetryChart';
import { EdgeGuardrail } from './components/EdgeGuardrail';
import { ClaudeLayer } from './components/ClaudeLayer';
import { ControlPanel } from './components/ControlPanel';
import { AuditLedger } from './components/AuditLedger';

function App() {
  const [state, setState] = useState<any>(null);
  const [uptime, setUptime] = useState(0);
  const startTime = useRef(Date.now());

  useEffect(() => {
    const fetchState = async () => {
      try {
        const res = await fetch('/api/state');
        if (res.ok) {
          const data = await res.json();
          setState(data);
        }
      } catch (err) {
        console.error("Failed to fetch state:", err);
      }
    };

    fetchState();
    const interval = setInterval(fetchState, 200);
    const uptimeInterval = setInterval(() => {
      setUptime(Math.floor((Date.now() - startTime.current) / 1000));
    }, 1000);

    return () => {
      clearInterval(interval);
      clearInterval(uptimeInterval);
    };
  }, []);

  const handleInject = async (type: 'fatal' | 'drift' | 'clear') => {
    try {
      await fetch('/api/inject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type })
      });
      if (state) {
        setState({
          ...state,
          injections: { fatal: type === 'fatal', drift: type === 'drift' }
        });
      }
    } catch (err) {
      console.error("Injection failed:", err);
    }
  };

  const handleOverride = async () => {
    try {
      await fetch('/api/override', { method: 'POST' });
    } catch (err) {
      console.error("Override failed:", err);
    }
  };

  const formatUptime = (s: number) =>
    `${String(Math.floor(s / 3600)).padStart(2, '0')}:${String(Math.floor((s % 3600) / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

  const isFatalActive = state?.injections?.fatal;
  const isDriftActive = state?.injections?.drift;
  const systemStatus = isFatalActive ? 'FAULT' : isDriftActive ? 'ANOMALY' : 'NOMINAL';
  const statusColor = isFatalActive ? 'text-red-400' : isDriftActive ? 'text-yellow-400' : 'text-emerald-400';

  if (!state) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center text-gray-500 bg-[var(--color-aerospace-bg)]">
        <Satellite className="w-12 h-12 mb-4 text-blue-500 animate-pulse" />
        <p className="font-mono text-sm">Initialising Mission Control…</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-aerospace-bg)] flex flex-col font-sans">

      {/* Top Nav Bar */}
      <header className="border-b border-[var(--color-aerospace-border)] bg-[var(--color-aerospace-panel)] px-6 py-3 flex items-center justify-between sticky top-0 z-10 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <Shield className="w-6 h-6 text-blue-500" />
          <div>
            <h1 className="text-base font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-400 leading-tight">
              SafeACS Mission Control
            </h1>
            <p className="text-[10px] text-gray-600 font-mono">Cyber-Physical AI Assurance Framework</p>
          </div>
        </div>

        {/* Live Status Bar */}
        <div className="hidden md:flex items-center gap-6 text-xs font-mono">
          <div className="flex items-center gap-1.5">
            <Circle className={`w-2 h-2 fill-current ${statusColor} ${systemStatus !== 'NOMINAL' ? 'animate-pulse' : ''}`} />
            <span className={statusColor}>SYS: {systemStatus}</span>
          </div>
          <div className="text-gray-500">
            UPTIME: <span className="text-gray-300">{formatUptime(uptime)}</span>
          </div>
          <div className="text-gray-500">
            GUARDRAIL: <span className="text-emerald-400">{state.latest_event?.guardrail?.latency_us?.toFixed(0) ?? '—'} µs</span>
          </div>
          <div className="text-gray-500">
            LLM: <span className={state.has_llm ? 'text-purple-400' : 'text-gray-600'}>{state.has_llm ? 'ACTIVE' : 'DISABLED'}</span>
          </div>
        </div>

        <a
          href="https://github.com/camirian/safe-acs"
          target="_blank"
          rel="noreferrer"
          className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors"
        >
          <Github className="w-4 h-4" />
          <span className="hidden sm:block">camirian/safe-acs</span>
        </a>
      </header>

      {/* Main Content */}
      <main className="flex-grow p-6">
        <div className="max-w-7xl mx-auto space-y-6">

          {/* Top Row: Telemetry & Controls */}
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            <div className="lg:col-span-3">
              <TelemetryChart data={state.rpms} />
            </div>
            <div className="lg:col-span-1">
              <ControlPanel onInject={handleInject} activeInjection={state.injections} />
            </div>
          </div>

          {/* Middle Row: The Bimodal Core */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <EdgeGuardrail event={state.latest_event} />
            <ClaudeLayer
              llmStatus={state.llm_analysis}
              hasLlm={state.has_llm}
              onOverride={handleOverride}
              latestEventType={state.latest_event?.outcome || ''}
            />
          </div>

          {/* Bottom Row: Audit Ledger */}
          <AuditLedger records={state.dr_ais_ledger} />

        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-[var(--color-aerospace-border)] px-6 py-3 text-center text-[11px] text-gray-700 font-mono">
        SafeACS — Bimodal Execution Topology · DO-178C / MIL-STD-882 / SysML v2 ·{' '}
        <a href="https://github.com/camirian/safe-acs" className="hover:text-gray-500 transition-colors" target="_blank" rel="noreferrer">
          github.com/camirian/safe-acs
        </a>
      </footer>
    </div>
  );
}

export default App;
