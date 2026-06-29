'use client'
import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '../../../../hooks/useAuth'
import { getInstrutor, atualizarInstrutor, getInstrutorPlanos, vincularPlanoInstrutor, desvincularPlanoInstrutor, getPlanos } from '../../../../lib/api'
import { InstrutorDetalheSkeleton } from './_skeleton'

export default function InstrutorDetalhe() {
  const { token } = useAuth()
  const { id } = useParams()
  const [instrutor, setInstrutor] = useState(null)
  const [planos, setPlanos] = useState([])
  const [todosPlanos, setTodosPlanos] = useState([])
  const [loading, setLoading] = useState(true)
  const [editando, setEditando] = useState(false)
  const [form, setForm] = useState({})
  const [planoSel, setPlanoSel] = useState('')
  const [salvando, setSalvando] = useState(false)
  const [erro, setErro] = useState('')
  const [toast, setToast] = useState(null)
  const [confirmandoDesvincular, setConfirmandoDesvincular] = useState(null)

  function exibirToast(msg, ok = true) {
    setToast({ msg, ok })
    setTimeout(() => setToast(null), 4000)
  }

  async function carregar(t) {
    const [i, p, tp] = await Promise.all([
      getInstrutor(t, id),
      getInstrutorPlanos(t, id),
      getPlanos(t),
    ])
    setInstrutor(i)
    setForm({
      especialidade: i.especialidade || '',
      modalidade: i.modalidade || '',
      salario: i.salario || '',
      data_admissao: i.data_admissao || '',
    })
    setPlanos(p)
    setTodosPlanos(tp)
  }

  useEffect(() => {
    if (!token) return
    async function init() {
      await carregar(token)
      setLoading(false)
    }
    init()
  }, [token, id])

  async function salvar() {
    setSalvando(true)
    setErro('')
    try {
      await atualizarInstrutor(token, id, {
        ...form,
        salario: form.salario ? parseFloat(form.salario) : undefined,
      })
      await carregar(token)
      setEditando(false)
      exibirToast('Dados do instrutor atualizados.')
    } catch (err) {
      setErro(err.message)
    }
    setSalvando(false)
  }

  async function vincular() {
    if (!planoSel) return
    setSalvando(true)
    setErro('')
    try {
      await vincularPlanoInstrutor(token, id, planoSel)
      setPlanoSel('')
      await carregar(token)
      exibirToast('Plano vinculado com sucesso.')
    } catch (err) {
      setErro(err.message)
    }
    setSalvando(false)
  }

  async function executarDesvincular(ipId) {
    setConfirmandoDesvincular(null)
    try {
      await desvincularPlanoInstrutor(token, id, ipId)
      await carregar(token)
      exibirToast('Vínculo removido.')
    } catch (err) {
      exibirToast(err.message, false)
    }
  }

  const input = "w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white"

  if (loading) return <InstrutorDetalheSkeleton />
  if (!instrutor) return <p className="text-red-500">Instrutor não encontrado.</p>

  const planosVinculadosIds = new Set(planos.map(ip => ip.plano_id))
  const planosDisponiveis = todosPlanos.filter(p => !planosVinculadosIds.has(p.id))

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3 flex-wrap">
        <Link href="/admin/instrutores" className="text-sm text-gray-500 hover:text-gray-700">← Instrutores</Link>
        <span className="text-gray-300">/</span>
        <h1 className="text-2xl font-bold text-gray-800">{instrutor.profiles?.nome}</h1>
        {!editando && (
          <button onClick={() => setEditando(true)}
            className="ml-auto border border-gray-200 bg-white hover:bg-gray-50 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium transition">
            ✏️ Editar
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Dados */}
        <div className="bg-white rounded-xl shadow-sm p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Dados do instrutor</h2>
          {editando ? (
            <div className="space-y-3">
              {[
                { label: 'Especialidade', key: 'especialidade', placeholder: 'Musculação, Natação...' },
                { label: 'Modalidade', key: 'modalidade', placeholder: 'Personal, Turma...' },
              ].map(({ label, key, placeholder }) => (
                <div key={key}>
                  <label className="text-xs text-gray-500">{label}</label>
                  <input className={input} value={form[key]}
                    onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                    placeholder={placeholder} />
                </div>
              ))}
              <div>
                <label className="text-xs text-gray-500">Salário (R$)</label>
                <input type="number" step="0.01" min="0" className={input} placeholder="Ex: 2500.00" value={form.salario}
                  onChange={e => setForm(f => ({ ...f, salario: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs text-gray-500">Data de admissão</label>
                <input type="date" className={input} value={form.data_admissao}
                  onChange={e => setForm(f => ({ ...f, data_admissao: e.target.value }))} />
              </div>
              {erro && <p className="text-xs text-red-500">{erro}</p>}
              <div className="flex gap-2 pt-1">
                <button onClick={salvar} disabled={salvando}
                  className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-1.5 rounded-lg text-sm font-medium transition disabled:opacity-60">
                  {salvando ? 'Salvando...' : 'Salvar'}
                </button>
                <button onClick={() => setEditando(false)}
                  className="border border-gray-200 text-gray-600 px-4 py-1.5 rounded-lg text-sm font-medium hover:bg-gray-50">
                  Cancelar
                </button>
              </div>
            </div>
          ) : (
            <dl className="space-y-2">
              {[
                ['Especialidade', instrutor.especialidade],
                ['Modalidade', instrutor.modalidade],
                ['Salário', instrutor.salario ? `R$ ${Number(instrutor.salario).toFixed(2)}` : null],
                ['Admissão', instrutor.data_admissao],
              ].map(([l, v]) => (
                <div key={l} className="flex justify-between py-1.5 border-b border-gray-50 last:border-0">
                  <dt className="text-sm text-gray-500">{l}</dt>
                  <dd className="text-sm font-medium text-gray-800">{v || '—'}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>

        {/* Planos */}
        <div className="bg-white rounded-xl shadow-sm p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Planos vinculados</h2>
          {planos.length === 0 ? (
            <p className="text-xs text-gray-400 mb-4">Nenhum plano vinculado.</p>
          ) : (
            <div className="space-y-2 mb-4">
              {planos.map(ip => (
                <div key={ip.id} className="flex justify-between items-center py-2 border-b border-gray-50 last:border-0">
                  <div>
                    <p className="text-sm font-medium text-gray-700">{ip.planos?.nome}</p>
                    <p className="text-xs text-gray-400">R$ {Number(ip.planos?.valor || 0).toFixed(2)}/mês</p>
                  </div>
                  {confirmandoDesvincular === ip.id ? (
                    <span className="flex items-center gap-2">
                      <span className="text-xs text-gray-600">Remover?</span>
                      <button onClick={() => executarDesvincular(ip.id)}
                        className="text-xs font-semibold text-red-600 hover:underline">
                        Sim
                      </button>
                      <button onClick={() => setConfirmandoDesvincular(null)}
                        className="text-xs text-gray-500 hover:underline">
                        Não
                      </button>
                    </span>
                  ) : (
                    <button onClick={() => setConfirmandoDesvincular(ip.id)}
                      className="text-xs text-red-400 hover:text-red-600 transition">
                      ✕ Remover
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}
          <div className="border-t pt-3 space-y-2">
            <p className="text-xs font-semibold text-gray-500">Vincular novo plano</p>
            {planosDisponiveis.length === 0 ? (
              <p className="text-xs text-gray-400">Todos os planos já estão vinculados.</p>
            ) : (
              <>
                <select className={input} value={planoSel} onChange={e => setPlanoSel(e.target.value)}>
                  <option value="">Selecione um plano...</option>
                  {planosDisponiveis.map(p => (
                    <option key={p.id} value={p.id}>{p.nome} — R$ {Number(p.valor).toFixed(2)}</option>
                  ))}
                </select>
                {erro && !editando && <p className="text-xs text-red-500">{erro}</p>}
                <button onClick={vincular} disabled={salvando}
                  className="w-full bg-orange-500 hover:bg-orange-600 text-white py-2 rounded-lg text-xs font-medium transition disabled:opacity-60">
                  {salvando ? 'Vinculando...' : 'Vincular plano'}
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {toast && (
        <div className={`fixed bottom-6 left-1/2 -translate-x-1/2 px-5 py-3 rounded-xl shadow-lg text-sm font-medium text-white z-50 max-w-sm text-center transition-all ${toast.ok ? 'bg-green-500' : 'bg-red-500'}`}>
          {toast.msg}
        </div>
      )}
    </div>
  )
}
