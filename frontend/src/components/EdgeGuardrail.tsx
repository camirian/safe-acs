import { ShieldAlert, ShieldCheck } from 'lucide-react';

interface GuardrailProps {
    event: any;
}

export function EdgeGuardrail({ event }: GuardrailProps) {
    if (!event) return (
        <div className="bg-[var(--color-aerospace-panel)] p-4 rounded-xl border border-[var(--color-aerospace-border)] h-full">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-300">
                <ShieldCheck className="text-gray-500" /> Edge Guardrail
            </h3>
            <p className="text-sm text-gray-500">Waiting for telemetry...</p>
        </div>
    );

    const fatal = event.guardrail?.has_fatal_violation;

    return (
        <div className={`bg-[var(--color-aerospace-panel)] p-4 rounded-xl border h-full transition-colors ${fatal ? 'border-red-500/50 bg-red-950/20' : 'border-[var(--color-aerospace-border)]'}`}>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-300">
                {fatal ? <ShieldAlert className="text-red-500" /> : <ShieldCheck className="text-emerald-500" />}
                Edge Guardrail
            </h3>

            {fatal ? (
                <div className="space-y-2">
                    <div className="text-red-400 font-bold">FATAL VIOLATION: Structural limit exceeded.</div>
                    <div className="text-sm border-l-2 border-red-500 pl-3 py-1 bg-red-900/10">
                        <span className="text-gray-400">Outcome:</span> <span className="font-mono text-xs">{event.outcome}</span>
                    </div>
                    <ul className="text-sm text-gray-400 list-disc pl-5 mt-2">
                        {event.guardrail.violations.map((v: any, i: number) => (
                            <li key={i}><span className="text-gray-300">{v.field}</span>: {v.message}</li>
                        ))}
                    </ul>
                </div>
            ) : (
                <div className="space-y-4">
                    <div className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        NOMINAL
                    </div>
                    <div className="text-sm text-gray-400">
                        Latency: <span className="text-emerald-400 font-mono">{event.guardrail?.latency_us?.toFixed(1)} µs</span>
                    </div>
                </div>
            )}
        </div>
    );
}
