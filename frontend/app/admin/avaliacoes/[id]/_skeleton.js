export function AvaliacaoDetalheSkeleton() {
  const p = 'animate-pulse rounded bg-gray-200 dark:bg-gray-700'
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3 flex-wrap">
          <div className={`${p} h-4 w-24`} />
          <div className={`${p} h-7 w-44`} />
          <div className={`${p} h-4 w-24`} />
        </div>
        <div className="flex gap-2">
          <div className={`${p} h-9 w-28 rounded-lg`} />
          <div className={`${p} h-9 w-24 rounded-lg`} />
        </div>
      </div>

      {/* 4 cards principais */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">
        {[
          ['Medidas principais', [55, 50, 60, 45, 40]],
          ['Circunferências',    [50, 55, 45, 50, 55]],
          ['Diâmetros ósseos',   [60, 55, 50, 60, 45, 55, 50, 60, 45]],
          ['Informações',        [50, 55, 45]],
        ].map(([titulo, linhas]) => (
          <div key={titulo} className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-5">
            <div className={`${p} h-4 w-36 mb-4`} />
            {linhas.map((w, i) => (
              <div key={i} className="flex justify-between py-1.5 border-b border-gray-50 dark:border-gray-700">
                <div className={`${p} h-3.5`} style={{ width: `${w * 0.55}%` }} />
                <div className={`${p} h-3.5`} style={{ width: `${w * 0.4}%` }} />
              </div>
            ))}
          </div>
        ))}
      </div>

      {/* Mapeamento corporal */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-5">
        <div className="flex items-center justify-between mb-4">
          <div className={`${p} h-4 w-44`} />
          <div className={`${p} h-7 w-40 rounded-full`} />
        </div>
        {/* Mini grid de medidas */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="bg-gray-50 dark:bg-gray-900/40 rounded-lg px-3 py-2 space-y-1.5">
              <div className={`${p} h-2.5 w-12`} />
              <div className={`${p} h-4 w-16`} />
            </div>
          ))}
        </div>
        {/* Silhueta placeholder */}
        <div className="flex justify-center">
          <div className={`${p} rounded-2xl`} style={{ width: 200, height: 340 }} />
        </div>
      </div>
    </div>
  )
}
