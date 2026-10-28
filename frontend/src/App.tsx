import { useEffect, useRef, useState } from 'react'
import { fetchExamples, fetchHealth, fetchSchema, isArabic, streamChat, type Example, type Field } from './api'
import { ChatMessage, type Message } from './components/ChatMessage'
import { Sidebar } from './components/Sidebar'

const newId = () => (crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random().toString(16).slice(2)}`)

export default function App() {
  const [sessionId, setSessionId] = useState(newId)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [examples, setExamples] = useState<Example[]>([])
  const [fields, setFields] = useState<Field[]>([])
  const [health, setHealth] = useState('connecting…')
  const bottom = useRef<HTMLDivElement>(null)
  const abort = useRef<AbortController | null>(null)

  useEffect(() => {
    fetchExamples().then(setExamples).catch(() => setExamples([]))
    fetchSchema().then((s) => setFields(s.fields)).catch(() => setFields([]))
    fetchHealth()
      .then((h) =>
        setHealth(
          `${h.documents.toLocaleString()} documents · ${h.llm_model}${h.llm_key_configured ? '' : ' · ⚠ no API key'}`,
        ),
      )
      .catch(() => setHealth('⚠ backend unreachable'))
  }, [])

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const patch = (id: string, fn: (m: Message) => Message) => setMessages((ms) => ms.map((m) => (m.id === id ? fn(m) : m)))

  async function send(text: string) {
    const message = text.trim()
    if (!message || busy) return
    setInput('')
    setBusy(true)
    const aid = newId()
    setMessages((ms) => [
      ...ms,
      { id: newId(), role: 'user', text: message, status: 'done', steps: [] },
      { id: aid, role: 'assistant', text: '', status: 'pending', steps: [] },
    ])
    abort.current = new AbortController()
    try {
      const response = await streamChat(
        sessionId,
        message,
        (step) => patch(aid, (m) => ({ ...m, steps: [...m.steps, step] })),
        abort.current.signal,
      )
      patch(aid, (m) => ({ ...m, status: 'done', response, text: response.answer, steps: response.steps }))
    } catch (err) {
      // Never show a raw exception/stack text in the UI - log it for debugging, show a friendly,
      // localized message instead (the error bubble already has a Retry button).
      console.error('chat request failed:', err)
      const friendly = isArabic(message)
        ? 'حدث خطأ أثناء محاولة الإجابة - يرجى المحاولة مرة أخرى.'
        : 'Something went wrong while answering that - please try again.'
      patch(aid, (m) => ({ ...m, status: 'error', text: friendly }))
    } finally {
      setBusy(false)
    }
  }

  function newChat() {
    abort.current?.abort()
    setMessages([])
    setSessionId(newId())
    setBusy(false)
  }

  const lastUser = [...messages].reverse().find((m) => m.role === 'user')
  const rtlInput = isArabic(input)
  // "UI language" for the sidebar: the most recent message's language, else the in-progress input.
  const lastMsg = messages.at(-1)
  const uiLang: 'en' | 'ar' =
    lastMsg?.response?.language === 'ar' || isArabic(lastMsg?.text ?? '') || (!lastMsg && rtlInput) ? 'ar' : 'en'

  return (
    <div className="flex h-full">
      <Sidebar fields={fields} health={health} uiLang={uiLang} onPickExample={(text) => send(text)} />
      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between bg-navy px-6 py-3 text-white">
          <div>
            <h1 className="text-base font-semibold">Procurement Assistant</h1>
            <p className="text-xs text-white/70">California state purchases · FY2012-13 → FY2014-15 · ask in English or Arabic</p>
          </div>
          <button
            onClick={newChat}
            className="rounded-full bg-amber px-4 py-1.5 text-sm font-medium text-navy transition hover:bg-amber-dark"
          >
            + New chat
          </button>
        </header>

        <div className="flex-1 overflow-y-auto bg-navy">
          <div className="mx-auto max-w-4xl space-y-4 px-4 py-6">
            {!messages.length && (
              <div className="py-10 text-center">
                <h2 className="text-xl font-semibold text-white">Ask anything about state procurement</h2>
                <p className="mt-1 text-sm text-white/70">
                  Your question is turned into a MongoDB aggregation, executed, and explained.
                </p>
              </div>
            )}
            {messages.map((m) => (
              <ChatMessage
                key={m.id}
                msg={m}
                onRetry={m.status === 'error' && lastUser ? () => send(lastUser.text) : undefined}
              />
            ))}
            <div ref={bottom} />
          </div>
        </div>

        <div className="border-t border-white/10 bg-navy">
          <div className="mx-auto max-w-4xl px-4 py-3">
            {!messages.length && examples.length > 0 && (
              <div className="mb-3 flex flex-wrap gap-2">
                {examples.map((e) => (
                  <button
                    key={e.text}
                    dir={e.lang === 'ar' ? 'rtl' : 'ltr'}
                    onClick={() => send(e.text)}
                    className="rounded-full bg-white/10 px-3 py-1 text-xs text-white transition hover:bg-amber hover:text-navy"
                  >
                    {e.text}
                  </button>
                ))}
              </div>
            )}
            <form
              onSubmit={(e) => {
                e.preventDefault()
                send(input)
              }}
              className="flex gap-2"
            >
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                dir={rtlInput ? 'rtl' : 'ltr'}
                placeholder="e.g. Which quarter had the highest spending?  /  كم عدد الطلبات في مارس 2014؟"
                className="flex-1 rounded-full border border-transparent bg-white px-4 py-2 text-sm text-navy outline-none focus:border-amber focus:ring-2 focus:ring-amber/30"
                disabled={busy}
              />
              <button
                type="submit"
                disabled={busy || !input.trim()}
                className="rounded-full bg-amber px-5 py-2 text-sm font-medium text-navy transition hover:bg-amber-dark disabled:opacity-50"
              >
                {busy ? 'Thinking…' : 'Send'}
              </button>
            </form>
          </div>
        </div>
      </main>
    </div>
  )
}
