'use client'
import { useEffect, useState } from 'react'
import { useAuth } from '../../../hooks/useAuth'
import { downloadRelatorio, getMe, getConfigAcademia } from '../../../lib/api'

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

const TODOS_RELATORIOS = [
  {
    titulo: 'Relatório de alunos',
    descricao: 'Lista completa com status, planos e contatos.',
    emoji: '👥',
    endpoint: '/relatorios/alunos',
    permCampo: null, // sem restrição para recepcionista
  },
  {
    titulo: 'Relatório financeiro',
    descricao: 'Mensalidades pagas, pendentes e atrasadas do mês.',
    emoji: '💰',
    endpoint: '/relatorios/financeiro',
    permCampo: 'relatorio_financeiro',
  },
  {
    titulo: 'Relatório de inadimplência',
    descricao: 'Alunos em atraso com dias de inadimplência.',
    emoji: '⚠️',
    endpoint: '/relatorios/inadimplencia',
    permCampo: 'relatorio_inadimplencia',
  },
]

export default function RelatoriosPage() {
  const { token } = useAuth()
  const [loading, setLoading] = useState(true)
  const [carregando, setCarregando] = useState({})
  const [userTipo, setUserTipo] = useState('')
  const [permsRecep, setPermsRecep] = useState({})
  const [toast, setToast] = useState(null)

  function exibirToast(msg, ok = true) {
    setToast({ msg, ok })
    setTimeout(() => setToast(null), 5000)
  }

  useEffect(() => {
    if (!token) return
    async function init() {
      try {
        const [me, config] = await Promise.all([getMe(token), getConfigAcademia(token)])
        setUserTipo(me.tipo)
        const perms = config.permissoes_recepcionista || {}
        setPermsRecep(perms)
        // Avisa sobre relatórios bloqueados via toast logo ao carregar
        if (me.tipo === 'recepcionista') {
          const bloqueados = TODOS_RELATORIOS.filter(r => r.permCampo && !perms[r.permCampo])
          if (bloqueados.length > 0) {
            const nomes = bloqueados.map(r => r.titulo).join(' e ')
            exibirToast(
              `${nomes} ${bloqueados.length === 1 ? 'está restrito' : 'estão restritos'} ao Administrador. Solicite acesso em Configurações → Academia.`,
              false
            )
          }
        }
      } catch { /* layout já trata sessão */ }
      setLoading(false)
    }
    init()
  }, [token])

  async function baixar(endpoint, formato) {
    setCarregando(l => ({ ...l, [endpoint]: true }))
    try {
      await downloadRelatorio(token, `${endpoint}?formato=${formato}`)
    } catch (err) {
      exibirToast(err.message, false)
    }
    setCarregando(l => ({ ...l, [endpoint]: false }))
  }

  const relatorios = TODOS_RELATORIOS.filter(r => {
    if (userTipo === 'admin') return true
    if (!r.permCampo) return true
    return !!permsRecep[r.permCampo]
  })

  if (loading) return <p className="text-gray-400">Carregando...</p>

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Relatórios</h1>
        <p className="text-sm text-gray-500 mt-1">Exporte os dados da academia em PDF ou Excel</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {relatorios.map(r => (
          <RelCard
            key={r.endpoint}
            titulo={r.titulo}
            descricao={r.descricao}
            emoji={r.emoji}
            carregando={carregando[r.endpoint]}
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

      {toast && (
        <div className={`fixed bottom-6 left-1/2 -translate-x-1/2 px-5 py-3 rounded-xl shadow-lg text-sm font-medium text-white z-50 max-w-sm text-center transition-all ${toast.ok ? 'bg-green-500' : 'bg-red-500'}`}>
          {toast.msg}
        </div>
      )}
    </div>
  )
}
