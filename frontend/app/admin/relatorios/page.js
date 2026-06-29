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
  const [erro, setErro] = useState('')
  const [userTipo, setUserTipo] = useState('')
  const [permsRecep, setPermsRecep] = useState({})

  useEffect(() => {
    if (!token) return
    async function init() {
      try {
        const [me, config] = await Promise.all([getMe(token), getConfigAcademia(token)])
        setUserTipo(me.tipo)
        setPermsRecep(config.permissoes_recepcionista || {})
      } catch { /* layout já trata sessão */ }
      setLoading(false)
    }
    init()
  }, [token])

  async function baixar(endpoint, formato) {
    setCarregando(l => ({ ...l, [endpoint]: true }))
    setErro('')
    try {
      await downloadRelatorio(token, `${endpoint}?formato=${formato}`)
    } catch (err) {
      setErro(err.message)
    }
    setCarregando(l => ({ ...l, [endpoint]: false }))
  }

  const relatorios = TODOS_RELATORIOS.filter(r => {
    if (userTipo === 'admin') return true
    if (!r.permCampo) return true // sem restrição
    return !!permsRecep[r.permCampo]
  })

  const bloqueados = userTipo === 'recepcionista'
    ? TODOS_RELATORIOS.filter(r => r.permCampo && !permsRecep[r.permCampo])
    : []

  if (loading) return <p className="text-gray-400">Carregando...</p>

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
            carregando={carregando[r.endpoint]}
            onDownload={(fmt) => baixar(r.endpoint, fmt)}
          />
        ))}
      </div>

      {/* Aviso quando recepcionista tem relatórios bloqueados */}
      {bloqueados.length > 0 && (
        <div className="bg-amber-50 border border-amber-100 rounded-xl p-4 mb-4">
          <p className="text-sm text-amber-700">
            <strong>Acesso restrito:</strong>{' '}
            {bloqueados.map(r => r.titulo).join(' e ')}{' '}
            {bloqueados.length === 1 ? 'está disponível' : 'estão disponíveis'} apenas para Administradores.
            Solicite ao administrador em{' '}
            <strong>Configurações → Academia</strong>.
          </p>
        </div>
      )}

      <div className="bg-orange-50 border border-orange-100 rounded-xl p-4">
        <p className="text-sm text-orange-700">
          <strong>Dica:</strong> O PDF é ideal para impressão e apresentações.
          O Excel permite filtros adicionais e análises personalizadas.
        </p>
      </div>
    </div>
  )
}
