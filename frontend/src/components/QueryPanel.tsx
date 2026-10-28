import { useState } from 'react'
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter'
import json from 'react-syntax-highlighter/dist/esm/languages/hljs/json'
import { github } from 'react-syntax-highlighter/dist/esm/styles/hljs'
import type { QueryResult } from '../api'

SyntaxHighlighter.registerLanguage('json', json)

/** Collapsible "Show query" panel with syntax-highlighted pipeline(s) and a copy button. */
export function QueryPanel({ results }: { results: QueryResult[] }) {
  const [open, setOpen] = useState(false)
  if (!results.length) return null
  return (
    <div className="rounded-lg border border-navy/10 bg-white" dir="ltr">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between px-3 py-2 text-left text-sm font-medium text-navy hover:bg-navy/5"
      >
        <span>
          {open ? '▾' : '▸'} Show query{results.length > 1 ? ` (${results.length} steps)` : ''}
        </span>
        <span className="text-xs font-normal text-navy/40">
          db.purchases.aggregate(…)
          {results.some((r) => r.retries) ? ` · ${results.reduce((a, r) => a + r.retries, 0)} self-correction(s)` : ''}
        </span>
      </button>
      {open && (
        <div className="space-y-3 border-t border-navy/10 p-3">
          {results.map((r, i) => (
            <PipelineBlock key={i} index={i} total={results.length} result={r} />
          ))}
        </div>
      )}
    </div>
  )
}

function PipelineBlock({ result, index, total }: { result: QueryResult; index: number; total: number }) {
  const [copied, setCopied] = useState(false)
  const code = JSON.stringify(result.pipeline, null, 2)
  const copy = async () => {
    await navigator.clipboard.writeText(`db.purchases.aggregate(${code})`)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <div>
      {total > 1 && <p className="mb-1 text-xs font-semibold text-navy/60">Step {index + 1}: {result.question}</p>}
      <div className="relative">
        <button
          onClick={copy}
          className="absolute right-2 top-2 rounded-full bg-white/90 px-2 py-0.5 text-xs text-navy ring-1 ring-navy/15 hover:bg-amber/20"
        >
          {copied ? 'Copied' : 'Copy'}
        </button>
        <SyntaxHighlighter
          language="json"
          style={github}
          customStyle={{ margin: 0, borderRadius: 6, fontSize: 12, maxHeight: 320, background: '#f9f0eb' }}
        >
          {code}
        </SyntaxHighlighter>
      </div>
      {result.error && <p className="mt-1 text-xs text-error">Error: {result.error}</p>}
    </div>
  )
}
