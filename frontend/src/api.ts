/** Typed client for the FastAPI backend (REST + SSE over fetch). */

export const API_URL = (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ?? 'http://localhost:8000'

export type Row = Record<string, unknown>

export interface StepEvent {
  node: string
  label: string
  ms: number
  detail: Record<string, unknown>
}

export interface QueryResult {
  question: string
  pipeline: Row[]
  rows: Row[]
  row_count: number
  truncated: boolean
  retries: number
  error: string | null
}

export interface ChartSpec {
  type: 'bar' | 'line'
  x: string
  y: string
  step: number
}

export interface ChatResponse {
  session_id: string
  answer: string
  language: 'en' | 'ar'
  intent: string
  standalone_question: string
  pipelines: Row[][]
  results: QueryResult[]
  chart: ChartSpec | null
  steps: StepEvent[]
  latency_ms: number
}

export interface Example { lang: 'en' | 'ar'; text: string }
export interface Field { name: string; type: string; notes: string }

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_URL}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json() as Promise<T>
}

export const fetchExamples = () => getJson<Example[]>('/api/examples')
export const fetchSchema = () => getJson<{ collection: string; fields: Field[] }>('/api/schema')
export const fetchHealth = () => getJson<{ status: string; documents: number; llm_model: string; llm_key_configured: boolean }>('/api/health')

/** POST /api/chat/stream and dispatch SSE events (`step`, `final`, `error`). */
export async function streamChat(
  sessionId: string,
  message: string,
  onStep: (s: StepEvent) => void,
  signal?: AbortSignal,
): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/api/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify({ session_id: sessionId, message }),
    signal,
  })
  if (!res.ok || !res.body) throw new Error(`Backend error ${res.status}: ${await res.text()}`)

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const blocks = buffer.split(/\r?\n\r?\n/)
    buffer = blocks.pop() ?? ''
    for (const block of blocks) {
      let event = 'message'
      const data: string[] = []
      for (const line of block.split(/\r?\n/)) {
        if (line.startsWith('event:')) event = line.slice(6).trim()
        else if (line.startsWith('data:')) data.push(line.slice(5).trimStart())
      }
      if (!data.length) continue
      const payload = JSON.parse(data.join('\n'))
      if (event === 'step') onStep(payload as StepEvent)
      else if (event === 'final') return payload as ChatResponse
      else if (event === 'error') throw new Error(payload.detail ?? 'Agent error')
    }
  }
  throw new Error('Stream ended without a final answer')
}

export const isArabic = (text: string) => /[؀-ۿ]/.test(text)
