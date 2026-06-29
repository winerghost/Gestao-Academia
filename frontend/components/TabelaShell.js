'use client'

export const TH = 'px-5 py-3 text-left text-[11px] font-semibold text-gray-400 uppercase tracking-wider whitespace-nowrap'
export const TD = 'px-5 py-3.5 text-sm'
export const BTN_ICON = 'p-1.5 rounded-lg text-gray-400 hover:text-gray-700 hover:bg-gray-100 transition-colors'

export default function TabelaShell({ loading, vazio, children }) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm flex justify-center py-16">
        <div className="w-5 h-5 border-2 border-orange-200 border-t-orange-500 rounded-full animate-spin" />
      </div>
    )
  }

  if (vazio) {
    return (
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm py-16 text-center text-sm text-gray-400">
        {typeof vazio === 'string' ? vazio : 'Nenhum registro encontrado.'}
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full">{children}</table>
      </div>
    </div>
  )
}
