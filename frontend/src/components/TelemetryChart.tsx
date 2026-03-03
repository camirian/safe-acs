import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ReferenceLine, ResponsiveContainer } from 'recharts';

interface TelemetryPoint {
    time: number;
    W1: number;
    W2: number;
    W3: number;
}

export function TelemetryChart({ data }: { data: TelemetryPoint[] }) {
    return (
        <div className="bg-[var(--color-aerospace-panel)] p-4 rounded-xl border border-[var(--color-aerospace-border)] h-96">
            <h3 className="text-lg font-semibold mb-4 text-gray-300">Reaction Wheel Telemetry (RPM)</h3>
            <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2d3748" />
                    <XAxis
                        dataKey="time"
                        stroke="#9ca3af"
                        tickFormatter={(val) => `${val}s`}
                        minTickGap={30}
                    />
                    <YAxis stroke="#9ca3af" domain={[-7000, 7000]} />
                    <Tooltip
                        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                        itemStyle={{ color: '#e5e7eb' }}
                    />

                    <ReferenceLine y={6000} label={{ position: 'top', value: 'GUARDRAIL (+6000)', fill: '#ef4444', fontSize: 12 }} stroke="#ef4444" strokeDasharray="3 3" />
                    <ReferenceLine y={-6000} label={{ position: 'bottom', value: 'GUARDRAIL (-6000)', fill: '#ef4444', fontSize: 12 }} stroke="#ef4444" strokeDasharray="3 3" />

                    <Line type="monotone" dataKey="W1" stroke="#10b981" dot={false} strokeWidth={2} isAnimationActive={false} />
                    <Line type="monotone" dataKey="W2" stroke="#eab308" dot={false} strokeWidth={2} isAnimationActive={false} />
                    <Line type="monotone" dataKey="W3" stroke="#3b82f6" dot={false} strokeWidth={2} isAnimationActive={false} />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}
