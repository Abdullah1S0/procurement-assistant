import { useEffect, useState } from 'react'
import type { Field } from '../api'
import { FIELD_HELP } from '../fieldHelp'

const STORAGE_KEY = 'sidebarCollapsed'

/** Collection schema reference: filterable field list, collapsible, with per-field example questions. */
export function Sidebar({
  fields,
  health,
  uiLang,
  onPickExample,
}: {
  fields: Field[]
  health: string
  uiLang: 'en' | 'ar'
  onPickExample: (text: string) => void
}) {
  const [q, setQ] = useState('')
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === '1'
    } catch {
      return false
    }
  })
  const [selected, setSelected] = useState<string | null>(null)

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, collapsed ? '1' : '0')
    } catch {
      /* ignore (private browsing, storage disabled, ...) */
    }
  }, [collapsed])

  const shown = fields.filter((f) => `${f.name} ${f.notes}`.toLowerCase().includes(q.toLowerCase()))

  if (collapsed) {
    return (
      <aside className="hidden w-10 shrink-0 flex-col items-center border-r border-navy/15 bg-amber py-4 lg:flex">
        <button
          onClick={() => setCollapsed(false)}
          title="Expand sidebar"
          aria-label="Expand sidebar"
          className="rounded-full p-1.5 text-navy transition hover:bg-amber-dark"
        >
          »
        </button>
      </aside>
    )
  }

  return (
    <aside className="hidden w-72 shrink-0 flex-col border-r border-navy/15 bg-amber lg:flex">
      <div className="border-b border-navy/15 p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-navy">procurement.purchases</h2>
          <button
            onClick={() => setCollapsed(true)}
            title="Collapse sidebar"
            aria-label="Collapse sidebar"
            className="rounded-full p-1 text-navy/60 transition hover:bg-amber-dark hover:text-navy"
          >
            «
          </button>
        </div>
        <p className="text-xs text-navy/70">{health}</p>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder={uiLang === 'ar' ? 'بحث في الحقول…' : 'Filter fields…'}
          dir={uiLang === 'ar' ? 'rtl' : 'ltr'}
          className="mt-2 w-full rounded-full border border-amber-dark bg-white/90 px-3 py-1 text-xs text-navy outline-none focus:border-amber-dark focus:ring-2 focus:ring-amber-dark/40"
        />
      </div>
      <ul className="flex-1 space-y-1 overflow-y-auto p-3 text-xs">
        {shown.map((f) => {
          const help = FIELD_HELP[f.name]
          const isOpen = selected === f.name
          const description = uiLang === 'ar' && help ? help.descriptionAr : f.notes
          const examples = help ? (uiLang === 'ar' ? help.examples.ar : help.examples.en) : []
          const header = (
            <div>
              <span className="font-mono font-medium text-navy">{f.name}</span>{' '}
              <span className="text-teal">{f.type}</span>
            </div>
          )
          const body = description && (
            <p dir={uiLang === 'ar' ? 'rtl' : 'ltr'} className="mt-0.5 text-navy/70">
              {description}
            </p>
          )
          // Technical/internal fields (no FIELD_HELP entry) have no example questions, so they
          // render as plain, non-interactive rows instead of a clickable button.
          if (!help) {
            return (
              <li key={f.name} className="rounded-lg px-2 py-1.5">
                {header}
                {body}
              </li>
            )
          }
          return (
            <li key={f.name} className="rounded-lg">
              <button
                onClick={() => setSelected(isOpen ? null : f.name)}
                className={`w-full rounded-lg px-2 py-1.5 text-left transition ${isOpen ? 'bg-amber-dark' : 'hover:bg-amber-dark/60'}`}
              >
                {header}
                {body}
              </button>
              {isOpen && examples.length > 0 && (
                <div className="mb-1 mt-1 flex flex-col gap-1 px-2">
                  {examples.map((ex) => (
                    <button
                      key={ex}
                      dir={uiLang === 'ar' ? 'rtl' : 'ltr'}
                      onClick={() => onPickExample(ex)}
                      className="rounded-full bg-white/70 px-2.5 py-1 text-left text-[11px] text-navy transition hover:bg-white"
                    >
                      {ex}
                    </button>
                  ))}
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </aside>
  )
}
