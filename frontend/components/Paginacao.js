'use client'

function calcPaginas(pagina, totalPaginas) {
  if (totalPaginas <= 7) {
    return Array.from({ length: totalPaginas }, (_, i) => i + 1)
  }
  const vizinhos = new Set([1, totalPaginas])
  for (let i = Math.max(1, pagina - 2); i <= Math.min(totalPaginas, pagina + 2); i++) {
    vizinhos.add(i)
  }
  const sorted = [...vizinhos].sort((a, b) => a - b)
  const result = []
  let prev = 0
  for (const p of sorted) {
    if (p - prev > 1) result.push(null) // null = reticências
    result.push(p)
    prev = p
  }
  return result
}

// onPagina(n): chamado com o número da nova página (inteiro).
export default function Paginacao({ pagina, totalPaginas, onPagina }) {
  const paginas = calcPaginas(pagina, totalPaginas)

  const base = 'min-w-[36px] h-9 flex items-center justify-center rounded-lg text-sm font-medium border transition'
  const padrao = 'border-gray-200 bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-40 disabled:cursor-not-allowed'
  const ativo  = 'border-orange-500 bg-orange-500 text-white cursor-default'

  return (
    <div className="flex items-center gap-1 flex-wrap">
      <button
        onClick={() => onPagina(Math.max(1, pagina - 1))}
        disabled={pagina <= 1}
        className={`${base} ${padrao} px-3`}
      >
        ← Anterior
      </button>

      {paginas.map((p, i) =>
        p === null
          ? <span key={`e${i}`} className="px-1 text-gray-400 select-none">…</span>
          : <button
              key={p}
              onClick={() => onPagina(p)}
              className={`${base} ${p === pagina ? ativo : padrao}`}
            >
              {p}
            </button>
      )}

      <button
        onClick={() => onPagina(Math.min(totalPaginas, pagina + 1))}
        disabled={pagina >= totalPaginas}
        className={`${base} ${padrao} px-3`}
      >
        Próxima →
      </button>
    </div>
  )
}
