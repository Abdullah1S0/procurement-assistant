# Frontend

React 19 + Vite + TypeScript + Tailwind v4 + Recharts.

```bash
npm install
cp .env.example .env     # VITE_API_URL=http://localhost:8000
npm run dev              # http://localhost:5173
npm run build            # typecheck + production build
```

- `src/api.ts`: typed REST client and an SSE parser (`fetch` + `ReadableStream`, because the stream endpoint is a POST)
- `src/components/`: `ChatMessage`, `StepIndicator` (live graph progress), `QueryPanel` (highlighted pipeline + copy),
  `ResultsTable`, `ResultChart`, `Sidebar` (schema)
- Arabic messages are rendered right-to-left automatically.
