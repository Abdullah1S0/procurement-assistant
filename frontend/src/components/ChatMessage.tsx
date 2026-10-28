import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { isArabic, type ChatResponse, type StepEvent } from '../api'
import { QueryPanel } from './QueryPanel'
import { ResultChart } from './ResultChart'
import { ResultsTable } from './ResultsTable'
import { StepIndicator } from './StepIndicator'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  text: string
  status: 'pending' | 'done' | 'error'
  steps: StepEvent[]
  response?: ChatResponse
}

/** One chat bubble. Assistant replies show answer, live steps, query panel, results table and chart. */
export function ChatMessage({ msg, onRetry }: { msg: Message; onRetry?: () => void }) {
  const rtl = isArabic(msg.text) || msg.response?.language === 'ar'
  if (msg.role === 'user') {
    return (
      <div className="flex justify-end">
        <div dir={rtl ? 'rtl' : 'ltr'} className="max-w-[80%] rounded-2xl rounded-br-sm bg-amber px-4 py-2 font-medium text-navy">
          {msg.text}
        </div>
      </div>
    )
  }
  const r = msg.response
  return (
    <div className="flex justify-start">
      <div className="w-full max-w-[90%] space-y-3 rounded-2xl rounded-bl-sm bg-white px-4 py-3 shadow-lg shadow-black/20">
        <StepIndicator steps={msg.steps} running={msg.status === 'pending'} />
        {msg.status === 'error' && (
          <div className="rounded-lg bg-error/10 px-3 py-2 text-sm text-error ring-1 ring-error/30">
            {msg.text}
            {onRetry && (
              <button onClick={onRetry} className="ml-2 underline">
                Retry
              </button>
            )}
          </div>
        )}
        {r && (
          <>
            <div dir={rtl ? 'rtl' : 'ltr'} className="prose prose-sm prose-slate max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{r.answer}</ReactMarkdown>
            </div>
            {r.chart && <ResultChart chart={r.chart} results={r.results} />}
            <Results response={r} />
            <QueryPanel results={r.results} />
            <p className="text-xs text-navy/40" dir="ltr">
              {(r.latency_ms / 1000).toFixed(1)}s
              {r.standalone_question && r.standalone_question !== msg.text ? ` · interpreted as: “${r.standalone_question}”` : ''}
            </p>
          </>
        )}
      </div>
    </div>
  )
}

function Results({ response }: { response: ChatResponse }) {
  const [tab, setTab] = useState(response.results.length - 1)
  if (!response.results.length) return null
  const shown = response.results[Math.min(tab, response.results.length - 1)]
  return (
    <div className="space-y-1">
      {response.results.length > 1 && (
        <div className="flex gap-1 text-xs" dir="ltr">
          {response.results.map((_, i) => (
            <button
              key={i}
              onClick={() => setTab(i)}
              className={`rounded-full px-2 py-0.5 ${i === tab ? 'bg-navy text-white' : 'bg-navy/5 text-navy/60'}`}
            >
              Step {i + 1}
            </button>
          ))}
        </div>
      )}
      <ResultsTable result={shown} lang={response.language} />
    </div>
  )
}
