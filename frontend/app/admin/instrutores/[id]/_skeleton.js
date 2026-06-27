export function InstrutorDetalheSkeleton() {
  const p = 'animate-pulse rounded bg-gray-200 dark:bg-gray-700'
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className={`${p} h-4 w-24`} />
        <div className={`${p} h-7 w-40`} />
        <div className={`${p} h-9 w-24 rounded-lg ml-auto`} />
      </div>

      {/* 2 cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Dados do instrutor */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-5 space-y-3">
          <div className={`${p} h-4 w-36 mb-4`} />
          {[70, 55, 45, 50].map((w, i) => (
            <div key={i} className="flex justify-between py-1.5 border-b border-gray-50 dark:border-gray-700">
              <div className={`${p} h-3.5`} style={{ width: `${w * 0.45}%` }} />
              <div className={`${p} h-3.5`} style={{ width: `${w * 0.4}%` }} />
            </div>
          ))}
        </div>

        {/* Planos vinculados */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm p-5 space-y-3">
          <div className={`${p} h-4 w-40 mb-4`} />
          {[80, 65, 75].map((w, i) => (
            <div key={i} className="flex justify-between items-center py-2 border-b border-gray-50 dark:border-gray-700">
              <div className="space-y-1.5">
                <div className={`${p} h-3.5`} style={{ width: `${w}px` }} />
                <div className={`${p} h-3`} style={{ width: `${w * 0.7}px` }} />
              </div>
              <div className={`${p} h-4 w-14`} />
            </div>
          ))}
          <div className="border-t pt-3 space-y-2">
            <div className={`${p} h-3 w-32`} />
            <div className={`${p} h-9 rounded-lg w-full`} />
            <div className={`${p} h-8 rounded-lg w-full`} />
          </div>
        </div>
      </div>
    </div>
  )
}
