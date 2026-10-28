import type { QueryResult } from '../api'
import { columnLabel } from '../fieldLabels'
import { formatValue } from '../format'

/** Small results table for one sub-query (first 50 rows from the API, 10 shown by default). */
export function ResultsTable({ result, lang }: { result: QueryResult; lang: 'en' | 'ar' }) {
  if (!result.rows.length) return <p className="text-xs text-navy/50">No rows returned.</p>
  // `label` is the backend's merged form of a compound _id (for charts); its parts are already columns
  const cols = Array.from(new Set(result.rows.flatMap((r) => Object.keys(r)))).filter((c) => c !== 'label')
  const rows = result.rows.slice(0, 10)
  return (
    <div className="overflow-x-auto rounded-lg border border-navy/10 bg-white" dir="ltr">
      <table className="min-w-full text-xs">
        <thead className="bg-navy/5 text-navy/60">
          <tr>
            {cols.map((c) => (
              <th key={c} className="px-3 py-1.5 text-left font-medium">{columnLabel(c, result.pipeline, lang)}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-navy/5">
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
        <p className="border-t border-navy/5 px-3 py-1 text-xs text-navy/40">
          Showing {rows.length} of {result.row_count} rows
        </p>
      )}
    </div>
  )
}
