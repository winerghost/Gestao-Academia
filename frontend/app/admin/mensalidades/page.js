'use client'
import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '../../../hooks/useAuth'
import { getMensalidades, pagarMensalidade } from '../../../lib/api'
import TabelaShell, { TH, TD, BTN_ICON } from '../../../components/TabelaShell'
import { IcoCheck } from '../../../components/IcoAcoes'

const BADGE = {
  paga:     'bg-green-50 text-green-700',
  pendente: 'bg-yellow-50 text-yellow-700',
  atrasada: 'bg-red-50 text-red-600',
}

const FILTROS = [
  { value: '', label: 'Todos' },
  { value: 'pendente', label: 'Pendentes' },
  { value: 'atrasada', label: 'Atrasadas' },
  { value: 'paga', label: 'Pagas' },
]

const COLUNAS = ['Aluno', 'Plano', 'Vencimento', 'Valor', 'Juros', 'Total', 'Status', 'Ações']

function fmt(v) {
  return Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2 })
}

function fmtData(s) {
  if (!s) return '—'
  const [ano, mes, dia] = s.split('-')
  return `${dia}/${mes}/${ano}`
}

export default function MensalidadesPage() {
  const { token } = useAuth()
  const [mensalidades, setMensalidades] = useState([])
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState('')
  const [mes, setMes] = useState('')
  const [confirmandoId, setConfirmandoId] = useState(null)
  const [pagandoId, setPagandoId] = useState(null)
  const [toast, setToast] = useState(null)

  function exibirToast(msg, tipo = 'erro') {
    setToast({ msg, tipo })
    setTimeout(() => setToast(null), 4000)
  }

  const carregar = useCallback(async (t, s, m) => {
    const params = {}
    if (s) params.status = s
    if (m) params.mes = m
    const data = await getMensalidades(t, params)
    setMensalidades(data)
  }, [])

  useEffect(() => {
    if (!token) return
    async function init() {
      await carregar(token, '', '')
      setLoading(false)
    }
    init()
  }, [token, carregar])

  useEffect(() => {
    if (token) carregar(token, status, mes)
  }, [status, mes, token, carregar])

  async function pagar(id) {
    setPagandoId(id)
    try {
      await pagarMensalidade(token, id)
      await carregar(token, status, mes)
      setConfirmandoId(null)
    } catch (err) {
      exibirToast(err.message || 'Erro ao registrar pagamento.')
    }
    setPagandoId(null)
  }

  const totalValor = mensalidades.reduce((s, m) => s + (m.valor_total || 0), 0)

  return (
    <div>
      {/* Cabeçalho */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Mensalidades</h1>
        <p className="text-sm text-gray-400 mt-0.5">
          {mensalidades.length} registro(s) — Total: R$ {fmt(totalValor)}
        </p>
      </div>

      {/* Toast */}
      {toast && (
        <div className={`mb-4 px-4 py-3 rounded-lg text-sm font-medium ${
          toast.tipo === 'sucesso' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
        }`}>
          {toast.msg}
        </div>
      )}

      {/* Filtros */}
      <div className="flex gap-2 mb-4 flex-wrap items-center">
        {FILTROS.map(f => (
          <button key={f.value} onClick={() => setStatus(f.value)}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition
              ${status === f.value ? 'bg-orange-500 text-white' : 'bg-white border border-gray-200 text-gray-500 hover:bg-gray-50'}`}>
            {f.label}
          </button>
        ))}
        <input type="month" value={mes} onChange={e => setMes(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400 bg-white" />
        {mes && (
          <button onClick={() => setMes('')} className="text-sm text-gray-400 hover:text-gray-600 transition">
            ✕ Limpar mês
          </button>
        )}
      </div>

      {/* Tabela */}
      <TabelaShell loading={loading} vazio={mensalidades.length === 0 && 'Nenhuma mensalidade encontrada.'}>
        <thead className="bg-gray-50 border-b border-gray-100">
          <tr>
            {COLUNAS.map(h => <th key={h} className={TH}>{h}</th>)}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {mensalidades.map(m => {
            const nomeAluno = m.aluno_planos?.alunos?.profiles?.nome || '—'
            const nomePlano = m.aluno_planos?.planos?.nome || '—'
            const confirmando = confirmandoId === m.id
            return (
              <tr key={m.id} className="hover:bg-gray-50/60 transition-colors">
                <td className={`${TD} font-medium text-gray-800`}>{nomeAluno}</td>
                <td className={`${TD} text-gray-500`}>{nomePlano}</td>
                <td className={`${TD} text-gray-500`}>{fmtData(m.data_vencimento)}</td>
                <td className={`${TD} text-gray-700`}>R$ {fmt(m.valor)}</td>
                <td className={`${TD} ${m.juros > 0 ? 'text-red-500' : 'text-gray-400'}`}>
                  {m.juros > 0 ? `R$ ${fmt(m.juros)}` : '—'}
                </td>
                <td className={`${TD} font-semibold text-gray-800`}>
                  R$ {fmt(m.valor_total)}
                </td>
                <td className={TD}>
                  <span className={`inline-flex items-center text-xs font-semibold px-2.5 py-0.5 rounded-full capitalize ${BADGE[m.status] ?? 'bg-gray-100 text-gray-500'}`}>
                    {m.status}
                  </span>
                </td>
                <td className={`${TD} min-w-[110px]`}>
                  {m.status === 'paga' ? (
                    <span className="text-xs text-gray-400">{fmtData(m.data_pagamento)}</span>
                  ) : confirmando ? (
                    <span className="flex items-center gap-1.5 text-xs">
                      <button
                        onClick={() => pagar(m.id)}
                        disabled={pagandoId === m.id}
                        className="px-2 py-1 rounded-md bg-green-500 text-white font-medium hover:bg-green-600 transition disabled:opacity-60">
                        {pagandoId === m.id ? '...' : 'Confirmar'}
                      </button>
                      <button
                        onClick={() => setConfirmandoId(null)}
                        className="px-2 py-1 rounded-md border border-gray-200 text-gray-500 hover:bg-gray-50 transition">
                        Não
                      </button>
                    </span>
                  ) : (
                    <button
                      onClick={() => setConfirmandoId(m.id)}
                      className={`${BTN_ICON} inline-flex items-center gap-1.5 text-xs font-medium text-green-600 hover:text-green-700 hover:bg-green-50`}
                      title="Registrar pagamento">
                      <IcoCheck size={14} />
                      Pagar
                    </button>
                  )}
                </td>
              </tr>
            )
          })}
        </tbody>
      </TabelaShell>
    </div>
  )
}
