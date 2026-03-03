import { useState, useEffect } from 'react';
import { Shield } from 'lucide-react';
import { TelemetryChart } from './components/TelemetryChart';
import { EdgeGuardrail } from './components/EdgeGuardrail';
import { ClaudeLayer } from './components/ClaudeLayer';
import { ControlPanel } from './components/ControlPanel';
import { AuditLedger } from './components/AuditLedger';

function App() {
  const [state, setState] = useState<any>(null);

  useEffect(() => {
    // Polling API for simulation state
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
    const interval = setInterval(fetchState, 200); // 5Hz UI refresh
    return () => clearInterval(interval);
  }, []);

  const handleInject = async (type: 'fatal' | 'drift' | 'clear') => {
    try {
      await fetch('/api/inject', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type })
      });
      // Optimistic update
      if (state) {
        setState({
          ...state,
          injections: {
            fatal: type === 'fatal',
            drift: type === 'drift'
          }
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

  if (!state) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-500">
        <div className="animate-pulse flex items-center gap-2">
          <Shield className="w-6 h-6" /> Connecting to Mission Control...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-aerospace-bg)] p-6 font-sans">
      <header className="mb-8 border-b border-[var(--color-aerospace-border)] pb-4">
        <div className="flex items-center gap-3">
          <Shield className="w-8 h-8 text-blue-500" />
          <div>
            <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-400">
              SafeACS Mission Control
            </h1>
            <p className="text-sm text-gray-500 font-mono mt-1">Cyber-Physical AI Assurance Framework — Bimodal Protocol Demo</p>
          </div>
        </div>
      </header>

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
        <div>
          <AuditLedger records={state.dr_ais_ledger} />
        </div>

      </div>
    </div>
  );
}

export default App;
