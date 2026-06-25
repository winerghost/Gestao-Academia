'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '../../../lib/supabase'
import { getPlanos, criarPlano, atualizarPlano, togglePlanoAtivo } from '../../../lib/api'

export default function PlanosPage() {
  const router = useRouter()
  const [planos, setPlanos] = useState([])
  const [token, setToken] = useState('')
  const [loading, setLoading] = useState(true)
  const [mostraForm, setMostraForm] = useState(false)
  const [editando, setEditando] = useState(null)
  const [form, setForm] = useState({ nome: '', descricao: '', valor: '', duracao_dias: '30' })
  const [erro, setErro] = useState('')
  const [salvando, setSalvando] = useState(false)

  async function carregar(t) {
    const data = await getPlanos(t)
    setPlanos(data)
  }

  useEffect(() => {
    async function init() {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) { router.replace('/login'); return }
      setToken(session.access_token)
      await carregar(session.access_token)
      setLoading(false)
    }
    init()
  }, [router])

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  function iniciarEdicao(p) {
    setEditando(p.id)
    setMostraForm(false)
    setForm({ nome: p.nome, descricao: p.descricao || '', valor: p.valor, duracao_dias: p.duracao_dias })
  }

  function cancelar() {
    setMostraForm(false)
    setEditando(null)
    setErro('')
    setForm({ nome: '', descricao: '', valor: '', duracao_dias: '30' })
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSalvando(true)
    setErro('')
    const body = { ...form, valor: parseFloat(form.valor), duracao_dias: parseInt(form.duracao_dias) }
    try {
      if (editando) {
        await atualizarPlano(token, editando, body)
      } else {
        await criarPlano(token, body)
      }
      cancelar()
      await carregar(token)
    } catch (err) {
      setErro(err.message)
    }
    setSalvando(false)
  }

  async function toggle(id) {
    try {
      await togglePlanoAtivo(token, id)
      await carregar(token)
    } catch (err) {
      alert(err.message)
    }
  }

  const input = "w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white"
  const mostraFormulario = mostraForm || editando !== null

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Planos</h1>
          <p className="text-sm text-gray-500 mt-1">{planos.length} plano(s) cadastrado(s)</p>
        </div>
        {!editando && (
          <button onClick={() => { setMostraForm(!mostraForm); setEditando(null) }}
            className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition">
            {mostraForm ? '✕ Fechar' : '➕ Novo plano'}
          </button>
        )}
      </div>

      {/* Formulário */}
      {mostraFormulario && (
        <div className="bg-white rounded-xl shadow-sm p-5 mb-6 max-w-2xl">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">
            {editando ? 'Editar plano' : 'Novo plano'}
          </h2>
          <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="text-xs text-gray-500 mb-1 block">Nome *</label>
              <input className={input} value={form.nome} onChange={e => set('nome', e.target.value)} required
                placeholder="Musculação, Natação, Crossfit..." />
            </div>
            <div className="col-span-2">
              <label className="text-xs text-gray-500 mb-1 block">Descrição</label>
              <input className={input} value={form.descricao} onChange={e => set('descricao', e.target.value)}
                placeholder="Descreva o que está incluso no plano..." />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Valor mensal (R$) *</label>
              <input type="number" step="0.01" min="0.01" className={input} value={form.valor}
                onChange={e => set('valor', e.target.value)} required placeholder="99.90" />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Duração (dias) *</label>
              <input type="number" min="1" className={input} value={form.duracao_dias}
                onChange={e => set('duracao_dias', e.target.value)} required />
            </div>
            {erro && <p className="col-span-2 text-sm text-red-500 bg-red-50 rounded-lg px-3 py-2">{erro}</p>}
            <div className="col-span-2 flex gap-3">
              <button type="submit" disabled={salvando}
                className="bg-orange-500 hover:bg-orange-600 text-white px-5 py-2 rounded-lg text-sm font-medium transition disabled:opacity-60">
                {salvando ? 'Salvando...' : editando ? 'Atualizar plano' : 'Criar plano'}
              </button>
              <button type="button" onClick={cancelar}
                className="border border-gray-200 text-gray-600 px-5 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition">
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Grid de planos */}
      {loading ? (
        <p className="text-gray-400">Carregando...</p>
      ) : planos.length === 0 ? (
        <p className="text-center text-gray-400 py-12">Nenhum plano cadastrado.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {planos.map(p => (
            <div key={p.id}
              className={`bg-white rounded-xl shadow-sm p-5 border-l-4 transition ${p.ativo !== false ? 'border-orange-500' : 'border-gray-200 opacity-70'}`}>
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1 min-w-0">
                  <h3 className="font-semibold text-gray-800 truncate">{p.nome}</h3>
                  {p.descricao && <p className="text-xs text-gray-400 mt-0.5 line-clamp-2">{p.descricao}</p>}
                </div>
                <span className={`ml-2 flex-shrink-0 text-xs px-2 py-0.5 rounded-full font-medium ${p.ativo !== false ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                  {p.ativo !== false ? 'Ativo' : 'Inativo'}
                </span>
              </div>
              <p className="text-2xl font-bold text-orange-500">
                R$ {Number(p.valor).toFixed(2)}
                <span className="text-sm font-normal text-gray-400">/mês</span>
              </p>
              <p className="text-xs text-gray-400 mt-1">{p.duracao_dias} dias por ciclo</p>
              <div className="flex gap-3 mt-4 pt-3 border-t border-gray-50">
                <button onClick={() => iniciarEdicao(p)}
                  className="text-xs text-gray-500 hover:text-orange-500 font-medium transition">
                  ✏️ Editar
                </button>
                <button onClick={() => toggle(p.id)}
                  className="text-xs text-gray-500 hover:text-orange-500 font-medium transition">
                  {p.ativo !== false ? '⏸ Desativar' : '▶ Ativar'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
