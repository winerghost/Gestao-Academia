'use client'
import { useEffect, useState, useCallback } from 'react'
import { useAuth } from '../../../hooks/useAuth'
import { getMensalidades, pagarMensalidade } from '../../../lib/api'

const BADGE = {
  paga: 'bg-green-100 text-green-700',
  pendente: 'bg-yellow-100 text-yellow-700',
  atrasada: 'bg-red-100 text-red-700',
}

const FILTROS = [
  { value: '', label: 'Todos' },
  { value: 'pendente', label: 'Pendentes' },
  { value: 'atrasada', label: 'Atrasadas' },
  { value: 'paga', label: 'Pagas' },
]

export default function MensalidadesPage() {
  const { token } = useAuth()
  const [mensalidades, setMensalidades] = useState([])
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState('')
  const [mes, setMes] = useState('')

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
    if (!confirm('Confirmar pagamento desta mensalidade?')) return
    try {
      await pagarMensalidade(token, id)
      await carregar(token, status, mes)
    } catch (err) {
      alert(err.message)
    }
  }

  const totalValor = mensalidades.reduce((s, m) => s + (m.valor_total || 0), 0)
  const totalPago = mensalidades.filter(m => m.status === 'paga').reduce((s, m) => s + (m.valor_total || 0), 0)

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Mensalidades</h1>
        <p className="text-sm text-gray-500 mt-1">
          {mensalidades.length} registro(s) — Valor total: R$ {totalValor.toFixed(2)}
          {status === 'paga' && ` — Pago: R$ ${totalPago.toFixed(2)}`}
        </p>
      </div>

      {/* Filtros */}
      <div className="flex gap-3 mb-4 flex-wrap items-center">
        {FILTROS.map(f => (
          <button key={f.value} onClick={() => setStatus(f.value)}
            className={`px-3 py-2 rounded-lg text-sm font-medium transition
              ${status === f.value ? 'bg-orange-500 text-white' : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'}`}>
            {f.label}
          </button>
        ))}
        <input type="month" value={mes} onChange={e => setMes(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white" />
        {mes && (
          <button onClick={() => setMes('')} className="text-sm text-gray-400 hover:text-gray-600">✕ Limpar mês</button>
        )}
      </div>

      {/* Tabela */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <p className="text-center text-gray-400 py-12">Carregando...</p>
        ) : mensalidades.length === 0 ? (
          <p className="text-center text-gray-400 py-12">Nenhuma mensalidade encontrada.</p>
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                {['Aluno', 'Plano', 'Vencimento', 'Valor', 'Juros', 'Total', 'Status', 'Ações'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {mensalidades.map(m => {
                const nomeAluno = m.aluno_planos?.alunos?.profiles?.nome || '—'
                const nomePlano = m.aluno_planos?.planos?.nome || '—'
                return (
                  <tr key={m.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-800">{nomeAluno}</td>
                    <td className="px-4 py-3 text-sm text-gray-500">{nomePlano}</td>
                    <td className="px-4 py-3 text-sm text-gray-500">{m.data_vencimento}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">R$ {Number(m.valor).toFixed(2)}</td>
                    <td className="px-4 py-3 text-sm text-red-500">
                      {m.juros > 0 ? `R$ ${Number(m.juros).toFixed(2)}` : '—'}
                    </td>
                    <td className="px-4 py-3 text-sm font-semibold text-gray-800">
                      R$ {Number(m.valor_total).toFixed(2)}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium capitalize ${BADGE[m.status]}`}>
                        {m.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {m.status !== 'paga' ? (
                        <button onClick={() => pagar(m.id)}
                          className="text-orange-500 hover:text-orange-700 text-xs font-medium">
                          Pagar
                        </button>
                      ) : (
                        <span className="text-xs text-gray-400">{m.data_pagamento}</span>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
          </div>
        )}
      </div>
    </div>
  )
}
