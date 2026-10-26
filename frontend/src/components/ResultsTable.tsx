import type { QueryResult } from '../api'
import { formatValue } from '../format'

/** Small results table for one sub-query (first 50 rows from the API, 10 shown by default). */
export function ResultsTable({ result }: { result: QueryResult }) {
  if (!result.rows.length) return <p className="text-xs text-slate-500">No rows returned.</p>
  // `label` is the backend's merged form of a compound _id (for charts); its parts are already columns
  const cols = Array.from(new Set(result.rows.flatMap((r) => Object.keys(r)))).filter((c) => c !== 'label')
  const rows = result.rows.slice(0, 10)
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white" dir="ltr">
      <table className="min-w-full text-xs">
        <thead className="bg-slate-50 text-slate-500">
          <tr>
            {cols.map((c) => (
              <th key={c} className="px-3 py-1.5 text-left font-medium">{c === '_id' ? 'group' : c}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((r, i) => (
            <tr key={i}>
              {cols.map((c) => (
                <td key={c} className={`px-3 py-1.5 ${typeof r[c] === 'number' ? 'text-right tabular-nums' : ''}`}>
                  {formatValue(r[c], c)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {result.row_count > rows.length && (
        <p className="border-t border-slate-100 px-3 py-1 text-xs text-slate-400">
          Showing {rows.length} of {result.row_count} rows
        </p>
      )}
    </div>
  )
}
