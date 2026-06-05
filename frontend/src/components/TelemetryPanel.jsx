import React from 'react';
import { Cpu, TerminalSquare } from 'lucide-react';

export default function TelemetryPanel({ graphState }) {
  return (
    <div className="flex flex-col h-full space-y-5">
      <div className="flex items-center gap-2.5 text-zinc-500 dark:text-zinc-400">
        <Cpu className="w-5 h-5 text-indigo-500 dark:text-indigo-400" strokeWidth={1.5} />
        <span className="text-xs font-semibold tracking-[0.2em] uppercase text-zinc-800 dark:text-zinc-300">System Telemetry</span>
      </div>
      
      {/* Real-time Token & Hit Metric Cards */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-white/50 dark:bg-white/[0.02] p-4 border border-zinc-200 dark:border-white/5 rounded-2xl shadow-sm hover:bg-white/80 dark:hover:bg-white/[0.04] transition-colors">
          <p className="text-[11px] uppercase font-semibold text-zinc-500 tracking-wider">Tokens Consumed</p>
          <p className="text-2xl font-bold text-indigo-600 dark:text-indigo-300 mt-1 font-mono">
            {graphState?.telemetry?.total_tokens ?? 0}
          </p>
        </div>
        <div className="bg-white/50 dark:bg-white/[0.02] p-4 border border-zinc-200 dark:border-white/5 rounded-2xl shadow-sm hover:bg-white/80 dark:hover:bg-white/[0.04] transition-colors">
          <p className="text-[11px] uppercase font-semibold text-zinc-500 tracking-wider">Global Hits</p>
          <p className="text-2xl font-bold text-emerald-600 dark:text-emerald-400 mt-1 font-mono">
            {graphState?.telemetry?.global_hits ?? 0}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2 text-zinc-500 dark:text-zinc-400 text-sm font-medium pt-3">
        <TerminalSquare className="w-4 h-4" strokeWidth={1.5} />
        <span>Live Graph Memory State Map</span>
      </div>

      {/* Interactive JSON State Tree Canvas */}
      <div className="flex-grow bg-white/80 dark:bg-black/40 border border-zinc-200 dark:border-white/5 rounded-2xl p-5 font-mono text-[13px] overflow-auto text-zinc-800 dark:text-zinc-300 shadow-inner custom-scrollbar relative">
        <div className="absolute top-0 left-0 w-full h-8 bg-gradient-to-b from-black/5 dark:from-black/20 to-transparent pointer-events-none rounded-t-2xl"></div>
        {graphState?.raw_graph_state ? (
          <pre className="whitespace-pre-wrap leading-relaxed">
            {JSON.stringify(graphState.raw_graph_state, null, 2)}
          </pre>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-zinc-400 dark:text-zinc-600 space-y-3">
            <TerminalSquare className="w-8 h-8 opacity-40 dark:opacity-20" strokeWidth={1} />
            <span className="italic text-xs font-medium">Awaiting execution cycle...</span>
          </div>
        )}
      </div>
    </div>
  );
}