import { AlertOctagon, Activity, PowerOff } from 'lucide-react';

interface ControlProps {
    onInject: (type: 'fatal' | 'drift' | 'clear') => void;
    activeInjection: { fatal: boolean; drift: boolean };
}

export function ControlPanel({ onInject, activeInjection }: ControlProps) {
    return (
        <div className="bg-[var(--color-aerospace-panel)] p-4 rounded-xl border border-[var(--color-aerospace-border)] h-full flex flex-col">
            <h3 className="text-lg font-semibold mb-2 text-gray-300">Fault Injection</h3>
            <p className="text-sm text-gray-500 mb-6">Manipulate the Kinetic-Twin Simulator</p>

            <div className="space-y-3 flex-grow">
                <button
                    onClick={() => onInject('fatal')}
                    disabled={activeInjection.fatal}
                    className={`w-full flex items-center justify-start gap-3 p-3 rounded-lg border transition-all text-sm font-medium
            ${activeInjection.fatal
                            ? 'bg-red-900/40 border-red-500/50 text-red-300 opacity-50 cursor-not-allowed'
                            : 'bg-[var(--color-aerospace-bg)] border-gray-700 text-gray-300 hover:border-red-500/50 hover:bg-red-950/20 hover:text-red-400'
                        }`}
                >
                    <AlertOctagon className="w-4 h-4" />
                    Inject Fatal Fault (W2 &gt; 6000 RPM)
                </button>

                <button
                    onClick={() => onInject('drift')}
                    disabled={activeInjection.drift}
                    className={`w-full flex items-center justify-start gap-3 p-3 rounded-lg border transition-all text-sm font-medium
            ${activeInjection.drift
                            ? 'bg-yellow-900/40 border-yellow-500/50 text-yellow-300 opacity-50 cursor-not-allowed'
                            : 'bg-[var(--color-aerospace-bg)] border-gray-700 text-gray-300 hover:border-yellow-500/50 hover:bg-yellow-950/20 hover:text-yellow-400'
                        }`}
                >
                    <Activity className="w-4 h-4" />
                    Inject LLM Anomaly (W3 Drift)
                </button>
            </div>

            <button
                onClick={() => onInject('clear')}
                disabled={!activeInjection.fatal && !activeInjection.drift}
                className={`mt-4 w-full flex items-center justify-center gap-3 p-3 rounded-lg border transition-all text-sm font-bold
          ${(!activeInjection.fatal && !activeInjection.drift)
                        ? 'bg-[var(--color-aerospace-bg)] border-gray-800 text-gray-600 cursor-not-allowed'
                        : 'bg-emerald-600 border-emerald-500 text-white hover:bg-emerald-500 shadow-lg shadow-emerald-900/20'
                    }`}
            >
                <PowerOff className="w-4 h-4" />
                Clear All Faults (Nominal)
            </button>
        </div>
    );
}
