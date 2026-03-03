import { BrainCircuit, Cpu, AlertTriangle, KeyRound } from 'lucide-react';

interface ClaudeProps {
    llmStatus: any;
    hasLlm: boolean;
    onOverride: () => void;
    latestEventType: string;
}

export function ClaudeLayer({ llmStatus, hasLlm, onOverride, latestEventType }: ClaudeProps) {
    if (!hasLlm) {
        return (
            <div className="bg-[var(--color-aerospace-panel)] p-4 rounded-xl border border-[var(--color-aerospace-border)] h-full opacity-75">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-400">
                    <BrainCircuit className="text-gray-500" /> Claude Cognitive Layer
                </h3>
                <p className="text-sm text-yellow-500/80 bg-yellow-500/10 px-3 py-2 rounded border border-yellow-500/20">
                    LLM Observer Disabled (No API Key).
                </p>
            </div>
        );
    }

    if (!llmStatus) {
        return (
            <div className="bg-[var(--color-aerospace-panel)] p-4 rounded-xl border border-[var(--color-aerospace-border)] h-full">
                <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-300">
                    <BrainCircuit className="text-purple-400" /> Claude Cognitive Layer
                </h3>
                <div className="flex items-center gap-2 text-sm text-gray-500">
                    <Cpu className="w-4 h-4 animate-pulse" /> Accumulating telemetry window...
                </div>
            </div>
        );
    }

    const isAnomaly = llmStatus.anomaly_detected;

    return (
        <div className={`bg-[var(--color-aerospace-panel)] p-4 rounded-xl border h-full transition-colors ${isAnomaly ? 'border-yellow-500/50 bg-yellow-950/20' : 'border-[var(--color-aerospace-border)]'}`}>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-gray-300">
                <BrainCircuit className={isAnomaly ? "text-yellow-400" : "text-purple-400"} />
                Claude Cognitive Layer
            </h3>

            {isAnomaly ? (
                <div className="space-y-3">
                    <div className="flex items-center justify-between">
                        <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-500/10 text-yellow-400 border border-yellow-500/20">
                            <AlertTriangle className="w-3 h-3" /> HEURISTIC ANOMALY DETECTED
                        </div>
                        <span className="text-xs text-gray-500 font-mono">Conf: {llmStatus.confidence.toFixed(2)}</span>
                    </div>

                    <div className="text-sm bg-[#171c26] p-3 rounded-lg border border-gray-800">
                        <div className="text-gray-400 mb-1 text-xs uppercase tracking-wider">Reasoning</div>
                        <div className="text-gray-300">{llmStatus.reasoning}</div>
                    </div>

                    <div className="text-sm flex items-center gap-2">
                        <span className="text-gray-400 text-xs uppercase tracking-wider">Recommended Action:</span>
                        <code className="text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded">{llmStatus.recommended_action}</code>
                    </div>

                    {latestEventType.includes("TYPE_1") && (
                        <button
                            onClick={onOverride}
                            className="mt-4 w-full flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white py-2 px-4 rounded-lg text-sm font-medium transition-all shadow-lg shadow-blue-900/20"
                        >
                            <KeyRound className="w-4 h-4" />
                            AUTHORIZE CRYPTOGRAPHIC COMMAND
                        </button>
                    )}
                </div>
            ) : (
                <div className="space-y-4">
                    <div className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/20">
                        NOMINAL PATTERN
                    </div>
                    <p className="text-sm text-gray-400">Continuous monitoring engaged. No anomalies detected in current window.</p>
                </div>
            )}
        </div>
    );
}
