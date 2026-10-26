import { useState } from 'react'
import type { Field } from '../api'

/** Collection schema reference. */
export function Sidebar({ fields, health }: { fields: Field[]; health: string }) {
  const [q, setQ] = useState('')
  const shown = fields.filter((f) => `${f.name} ${f.notes}`.toLowerCase().includes(q.toLowerCase()))
  return (
    <aside className="hidden w-72 shrink-0 flex-col border-r border-slate-200 bg-white lg:flex">
      <div className="border-b border-slate-200 p-4">
        <h2 className="text-sm font-semibold">procurement.purchases</h2>
        <p className="text-xs text-slate-500">{health}</p>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Filter fields…"
          className="mt-2 w-full rounded-md border border-slate-200 px-2 py-1 text-xs outline-none focus:border-indigo-400"
        />
      </div>
      <ul className="flex-1 space-y-2 overflow-y-auto p-4 text-xs">
        {shown.map((f) => (
          <li key={f.name}>
            <span className="font-mono font-medium text-slate-800">{f.name}</span>{' '}
            <span className="text-indigo-600">{f.type}</span>
            {f.notes && <p className="text-slate-500">{f.notes}</p>}
          </li>
        ))}
      </ul>
    </aside>
  )
}
