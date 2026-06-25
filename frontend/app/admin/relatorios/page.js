'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '../../../lib/supabase'
import { downloadRelatorio } from '../../../lib/api'

function RelCard({ titulo, descricao, emoji, onDownload, carregando }) {
  const [formato, setFormato] = useState('pdf')
  return (
    <div className="bg-white rounded-xl shadow-sm p-5">
      <div className="flex items-start gap-3 mb-4">
        <span className="text-3xl">{emoji}</span>
        <div>
          <h3 className="font-semibold text-gray-800">{titulo}</h3>
          <p className="text-sm text-gray-400 mt-0.5">{descricao}</p>
        </div>
      </div>
      <div className="flex gap-2 items-center">
        <select value={formato} onChange={e => setFormato(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white">
          <option value="pdf">PDF</option>
          <option value="excel">Excel</option>
        </select>
        <button onClick={() => onDownload(formato)} disabled={carregando}
          className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-1.5 rounded-lg text-sm font-medium transition disabled:opacity-60 flex items-center gap-2">
          {carregando ? '⏳ Gerando...' : '⬇️ Baixar'}
        </button>
      </div>
    </div>
  )
}

export default function RelatoriosPage() {
  const router = useRouter()
  const [loading, setLoading] = useState({})
  const [erro, setErro] = useState('')

  async function baixar(endpoint, formato) {
    const { data: { session } } = await supabase.auth.getSession()
    if (!session) { router.replace('/login'); return }
    setLoading(l => ({ ...l, [endpoint]: true }))
    setErro('')
    try {
      await downloadRelatorio(session.access_token, `${endpoint}?formato=${formato}`)
    } catch (err) {
      setErro(err.message)
    }
    setLoading(l => ({ ...l, [endpoint]: false }))
  }

  const relatorios = [
    {
      titulo: 'Relatório de alunos',
      descricao: 'Lista completa com status, planos e contatos.',
      emoji: '👥',
      endpoint: '/relatorios/alunos',
    },
    {
      titulo: 'Relatório financeiro',
      descricao: 'Mensalidades pagas, pendentes e atrasadas do mês.',
      emoji: '💰',
      endpoint: '/relatorios/financeiro',
    },
    {
      titulo: 'Relatório de inadimplência',
      descricao: 'Alunos em atraso com dias de inadimplência.',
      emoji: '⚠️',
      endpoint: '/relatorios/inadimplencia',
    },
  ]

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Relatórios</h1>
        <p className="text-sm text-gray-500 mt-1">Exporte os dados da academia em PDF ou Excel</p>
      </div>

      {erro && (
        <div className="mb-4 text-sm text-red-500 bg-red-50 border border-red-100 rounded-xl px-4 py-3">
          {erro}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {relatorios.map(r => (
          <RelCard
            key={r.endpoint}
            titulo={r.titulo}
            descricao={r.descricao}
            emoji={r.emoji}
            carregando={loading[r.endpoint]}
            onDownload={(fmt) => baixar(r.endpoint, fmt)}
          />
        ))}
      </div>

      <div className="bg-orange-50 border border-orange-100 rounded-xl p-4">
        <p className="text-sm text-orange-700">
          <strong>Dica:</strong> O PDF é ideal para impressão e apresentações.
          O Excel permite filtros adicionais e análises personalizadas.
        </p>
      </div>
    </div>
  )
}
