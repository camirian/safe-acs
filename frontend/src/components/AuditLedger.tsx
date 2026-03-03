import { Terminal } from 'lucide-react';

interface LedgerProps {
    records: any[];
}

export function AuditLedger({ records }: LedgerProps) {
    return (
        <div className="bg-[var(--color-aerospace-panel)] rounded-xl border border-[var(--color-aerospace-border)] flex flex-col overflow-hidden h-64">
            <div className="bg-[var(--color-aerospace-bg)] border-b border-[var(--color-aerospace-border)] p-3 flex items-center gap-2">
                <Terminal className="w-4 h-4 text-gray-500" />
                <h3 className="text-sm font-semibold text-gray-400 font-mono">DR-AIS Immutable Ledger (JSONL Stream)</h3>
            </div>

            <div className="p-4 overflow-y-auto flex-grow bg-[#0a0f18] font-mono text-[11px] leading-relaxed text-gray-400">
                {records.length === 0 ? (
                    <div className="text-gray-600 italic">Waiting for DR-AIS audit records...</div>
                ) : (
                    <div className="space-y-1">
                        {records.map((r, i) => {
                            // Highlight anomalies and violations in the log stream
                            const isError = r.outcome.includes('VIOLATION');
                            const isAnomaly = r.outcome.includes('ANOMALY');
                            const colorClass = isError ? 'text-red-400' : (isAnomaly ? 'text-yellow-400' : 'text-emerald-400');

                            return (
                                <div key={i} className="flex gap-4 hover:bg-white/5 px-2 py-0.5 rounded">
                                    <span className="text-gray-600 shrink-0">{r.logged_at_utc.split('T')[1].replace('Z', '')}</span>
                                    <span className={`shrink-0 w-64 ${colorClass}`}>{r.outcome}</span>
                                    <span className="text-gray-500 truncate">
                                        {JSON.stringify({
                                            latency: `${r.guardrail?.latency_us?.toFixed(1)}us`,
                                            tokens: r.rocs_telemetry?.total_tokens || 0,
                                            actuation: r.actuation_approved
                                        })}
                                    </span>
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
        </div>
    );
}
