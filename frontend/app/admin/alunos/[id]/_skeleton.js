// Skeleton da página de detalhe do aluno — exibido durante navegação e fetch.
export function AlunoDetalheSkeleton() {
  const pulse = 'animate-pulse rounded bg-gray-200'
  const pulseD = 'animate-pulse rounded bg-gray-700'

  // Detecta dark mode via CSS var (já que o componente pode ser renderizado
  // pelo loading.js antes do React montar, usamos classes Tailwind diretas).
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 flex-wrap">
          <div className={`${pulse} dark:bg-gray-700 h-4 w-16`} />
          <div className={`${pulse} dark:bg-gray-700 h-7 w-48`} />
          <div className={`${pulse} dark:bg-gray-700 h-5 w-20 rounded-full`} />
        </div>
        <div className={`${pulse} dark:bg-gray-700 h-9 w-24 rounded-lg`} />
      </div>

      {/* 3 cards superiores */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {[1, 2, 3].map(i => (
          <div key={i} className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-5 space-y-3">
            <div className={`${pulse} dark:bg-gray-700 h-4 w-32 mb-4`} />
            {[80, 60, 90, 70, 55].map((w, j) => (
              <div key={j} className="flex justify-between py-1.5 border-b border-gray-50 dark:border-gray-700">
                <div className={`${pulse} dark:bg-gray-700 h-3.5`} style={{ width: `${w * 0.4}%` }} />
                <div className={`${pulse} dark:bg-gray-700 h-3.5`} style={{ width: `${w * 0.35}%` }} />
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Tabela avaliações */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700 flex items-center justify-between">
          <div className={`${pulse} dark:bg-gray-700 h-4 w-36`} />
          <div className={`${pulse} dark:bg-gray-700 h-4 w-24`} />
        </div>
        <SkeletonTable cols={6} rows={2} />
      </div>

      {/* Tabela mensalidades */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700">
          <div className={`${pulse} dark:bg-gray-700 h-4 w-28`} />
        </div>
        <SkeletonTable cols={7} rows={4} />
      </div>
    </div>
  )
}

function SkeletonTable({ cols, rows }) {
  const pulse = 'animate-pulse rounded bg-gray-200 dark:bg-gray-700'
  const widths = [55, 40, 35, 30, 30, 35, 25]
  return (
    <table className="w-full">
      <thead className="bg-gray-50 dark:bg-gray-900/40">
        <tr>
          {Array.from({ length: cols }).map((_, i) => (
            <th key={i} className="px-4 py-2.5">
              <div className={`${pulse} h-3`} style={{ width: `${widths[i] || 40}%` }} />
            </th>
          ))}
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-50 dark:divide-gray-700">
        {Array.from({ length: rows }).map((_, r) => (
          <tr key={r}>
            {Array.from({ length: cols }).map((_, c) => (
              <td key={c} className="px-4 py-3">
                <div className={`${pulse} h-3.5`} style={{ width: `${widths[c] || 40}%` }} />
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  )
}
