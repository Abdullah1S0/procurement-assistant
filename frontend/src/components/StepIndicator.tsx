import type { StepEvent } from '../api'

const ORDER = ['understand', 'plan', 'generate_query', 'schema_lookup', 'validate', 'execute', 'reflect', 'answer']

/** Live node-by-node progress from the SSE stream (and the final trace once done). */
export function StepIndicator({ steps, running }: { steps: StepEvent[]; running: boolean }) {
  if (!steps.length && !running) return null
  return (
    <ol className="flex flex-wrap items-center gap-1.5 text-xs" dir="ltr">
      {steps.map((s, i) => {
        const failed = s.detail?.ok === false || s.node === 'reflect'
        return (
          <li
            key={i}
            title={JSON.stringify(s.detail, null, 1)}
            className={`rounded-full px-2 py-0.5 ring-1 ${
              failed ? 'bg-amber-50 text-amber-800 ring-amber-200' : 'bg-emerald-50 text-emerald-800 ring-emerald-200'
            }`}
          >
            {failed ? '↻' : '✓'} {s.label}
            <span className="ml-1 text-slate-400">{s.ms >= 1000 ? `${(s.ms / 1000).toFixed(1)}s` : `${s.ms}ms`}</span>
          </li>
        )
      })}
      {running && (
        <li className="flex items-center gap-1 rounded-full bg-indigo-50 px-2 py-0.5 text-indigo-700 ring-1 ring-indigo-200">
          <span className="h-2 w-2 animate-pulse rounded-full bg-indigo-500" />
          {nextLabel(steps)}…
        </li>
      )}
    </ol>
  )
}

function nextLabel(steps: StepEvent[]): string {
  const last = steps.at(-1)?.node
  if (!last) return 'Understanding the question'
  const next: Record<string, string> = {
    understand: 'Planning',
    plan: 'Generating query',
    generate_query: 'Validating query',
    schema_lookup: 'Generating query',
    validate: 'Executing on MongoDB',
    execute: 'Writing the answer',
    reflect: 'Regenerating query',
  }
  return next[last] ?? ORDER[0]
}
