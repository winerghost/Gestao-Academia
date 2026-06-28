'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useAuth } from '../../../../hooks/useAuth'
import { getConfigAcademia, atualizarConfigAcademia } from '../../../../lib/api'

const btn = 'text-white px-5 py-2 rounded-lg text-sm font-medium transition disabled:opacity-60'
const btnStyle = { backgroundColor: 'var(--cor-destaque)' }

function Toggle({ checked, onChange }) {
  return (
    <button type="button" onClick={() => onChange(!checked)}
      className="relative w-11 h-6 rounded-full transition-colors flex-shrink-0"
      style={{ backgroundColor: checked ? 'var(--cor-destaque)' : '#d1d5db' }}
      aria-pressed={checked}
    >
      <span className="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform"
        style={{ transform: checked ? 'translateX(20px)' : 'translateX(0)' }} />
    </button>
  )
}

export default function NotificacoesPage() {
  const { token } = useAuth()
  const [loading, setLoading] = useState(true)
  const [salvando, setSalvando] = useState(false)
  const [msg, setMsg] = useState({ tipo: '', texto: '' })

  const [cfg, setCfg] = useState({
    notif_lembrete_ativo: true,
    notif_dias_antes: 1,
    notif_atraso_ativo: true,
  })

  useEffect(() => {
    if (!token) return
    async function init() {
      try {
        const c = await getConfigAcademia(token)
        setCfg({
          notif_lembrete_ativo: c.notif_lembrete_ativo ?? true,
          notif_dias_antes: c.notif_dias_antes ?? 1,
          notif_atraso_ativo: c.notif_atraso_ativo ?? true,
        })
      } catch (err) {
        setMsg({ tipo: 'erro', texto: err.message })
      }
      setLoading(false)
    }
    init()
  }, [token])

  async function salvar(e) {
    e.preventDefault()
    setSalvando(true)
    setMsg({ tipo: '', texto: '' })
    try {
      await atualizarConfigAcademia(token, {
        notif_lembrete_ativo: cfg.notif_lembrete_ativo,
        notif_dias_antes: Number(cfg.notif_dias_antes),
        notif_atraso_ativo: cfg.notif_atraso_ativo,
      })
      setMsg({ tipo: 'ok', texto: 'Preferências de notificação salvas.' })
    } catch (err) {
      setMsg({ tipo: 'erro', texto: err.message })
    }
    setSalvando(false)
  }

  if (loading) return <p className="text-gray-400">Carregando...</p>

  return (
    <div className="max-w-2xl">
      <Link href="/admin/configuracoes" className="text-sm text-gray-500 hover:text-gray-700">
        ‹ Voltar para Configurações
      </Link>
      <h1 className="text-2xl font-bold text-gray-800 mt-2 mb-1">Notificações</h1>
      <p className="text-sm text-gray-500 mb-6">
        E-mails automáticos de cobrança enviados aos alunos.
      </p>

      <form onSubmit={salvar} className="bg-white rounded-xl shadow-sm p-5 space-y-5">
        {/* Lembrete de vencimento */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-gray-700">Lembrete de vencimento</p>
            <p className="text-xs text-gray-400 mt-0.5">
              Avisa o aluno por e-mail antes da mensalidade vencer.
            </p>
          </div>
          <Toggle checked={cfg.notif_lembrete_ativo}
            onChange={v => setCfg(c => ({ ...c, notif_lembrete_ativo: v }))} />
        </div>

        {cfg.notif_lembrete_ativo && (
          <div className="pl-1">
            <label className="text-xs text-gray-500 mb-1 block">Antecedência (dias antes do vencimento)</label>
            <input type="number" min="0" max="30"
              className="w-28 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2"
              style={{ '--tw-ring-color': 'var(--cor-destaque)' }}
              value={cfg.notif_dias_antes}
              onChange={e => setCfg(c => ({ ...c, notif_dias_antes: e.target.value }))} />
          </div>
        )}

        <hr className="border-gray-100" />

        {/* Aviso de atraso */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm font-medium text-gray-700">Aviso de atraso</p>
            <p className="text-xs text-gray-400 mt-0.5">
              Envia e-mail para alunos com mensalidades em atraso.
            </p>
          </div>
          <Toggle checked={cfg.notif_atraso_ativo}
            onChange={v => setCfg(c => ({ ...c, notif_atraso_ativo: v }))} />
        </div>

        <div className="flex items-center gap-3 pt-1">
          <button type="submit" className={btn} style={btnStyle} disabled={salvando}>
            {salvando ? 'Salvando...' : 'Salvar'}
          </button>
          {msg.texto && (
            <p className={`text-sm rounded-lg px-3 py-2 ${msg.tipo === 'erro' ? 'text-red-600 bg-red-50' : 'text-green-700 bg-green-50'}`}>
              {msg.texto}
            </p>
          )}
        </div>
      </form>
    </div>
  )
}
