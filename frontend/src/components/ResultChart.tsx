import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ChartSpec, QueryResult } from '../api'
import { compactNumber, formatValue } from '../format'

// Brand chart palette: teal primary, blue secondary, amber third - cycled across categories.
const SERIES_COLORS = ['#044b4e', '#10509a', '#ffb300']

/** Auto chart (bar or line) when the backend suggests one. */
export function ResultChart({ chart, results }: { chart: ChartSpec; results: QueryResult[] }) {
  const result = results[chart.step] ?? results.at(-1)
  if (!result) return null
  const data = result.rows.slice(0, 30).map((r) => ({ x: String(r[chart.x] ?? ''), y: Number(r[chart.y] ?? 0) }))
  const fmt = (v: number) => formatValue(v, chart.y)
  const axis = { tick: { fontSize: 11 }, stroke: '#27394c99' }
  const long = data.some((d) => d.x.length > 14)
  return (
    <div className="h-64 rounded-lg border border-navy/10 bg-white p-2" dir="ltr">
      <ResponsiveContainer width="100%" height="100%">
        {chart.type === 'line' ? (
          <LineChart data={data} margin={{ left: 8, right: 16, top: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27394c1a" />
            <XAxis dataKey="x" {...axis} />
            <YAxis tickFormatter={compactNumber} {...axis} />
            <Tooltip formatter={(v) => [fmt(Number(v)), chart.y]} />
            <Line type="monotone" dataKey="y" stroke={SERIES_COLORS[0]} strokeWidth={2} dot={{ r: 3 }} isAnimationActive={false} />
          </LineChart>
        ) : (
          <BarChart data={data} margin={{ left: 8, right: 16, top: 8, bottom: long ? 40 : 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#27394c1a" />
            <XAxis
              dataKey="x"
              {...axis}
              interval={0}
              angle={long ? -25 : 0}
              textAnchor={long ? 'end' : 'middle'}
              tickFormatter={(v: string) => (v.length > 22 ? `${v.slice(0, 21)}…` : v)}
            />
            <YAxis tickFormatter={compactNumber} {...axis} />
            <Tooltip formatter={(v) => [fmt(Number(v)), chart.y]} />
            <Bar dataKey="y" radius={[4, 4, 0, 0]} isAnimationActive={false}>
              {data.map((_, i) => (
                <Cell key={i} fill={SERIES_COLORS[i % SERIES_COLORS.length]} />
              ))}
            </Bar>
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}
