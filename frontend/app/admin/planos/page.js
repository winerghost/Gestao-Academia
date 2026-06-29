'use client'
import { useEffect, useState } from 'react'
import { useAuth } from '../../../hooks/useAuth'
import { getPlanos, criarPlano, atualizarPlano, togglePlanoAtivo } from '../../../lib/api'

const CORES = ['#607d8b', '#00897b', '#f57c00', '#6d4c8a']

function formatValor(v) {
  return Number(v).toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function PlanoCard({ p, index, onEditar, onToggle }) {
  const cor = CORES[index % CORES.length]
  const itens = p.descricao
    ? p.descricao.split(/[\n;]/).map(s => s.trim()).filter(Boolean)
    : []

  return (
    <div className={`rounded-xl overflow-hidden shadow-md flex flex-col ${p.ativo === false ? 'opacity-60' : ''}`}>
      {/* Header colorido */}
      <div className="p-5 text-white" style={{ backgroundColor: cor }}>
        <div className="flex items-start justify-between mb-2">
          <h3 className="text-lg font-bold leading-tight">{p.nome}</h3>
          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ml-2 flex-shrink-0 ${
            p.ativo !== false ? 'bg-white/25 text-white' : 'bg-black/20 text-white/70'
          }`}>
            {p.ativo !== false ? 'Ativo' : 'Inativo'}
          </span>
        </div>

        {p.descricao && (
          <p className="text-xs text-white/70 mb-4 line-clamp-2">{p.descricao}</p>
        )}

        <div className="flex items-baseline gap-1">
          <span className="text-sm font-medium opacity-80">R$</span>
          <span className="text-3xl font-extrabold">{formatValor(p.valor)}</span>
        </div>
        <p className="text-xs text-white/60 mt-1">{p.duracao_dias} dias por ciclo</p>
      </div>

      {/* Lista de itens */}
      <div className="flex-1 bg-white px-5 py-4">
        {itens.length > 0 ? (
          <ul className="space-y-2">
            {itens.map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-gray-600">
                <span className="mt-0.5 flex-shrink-0 font-bold text-base leading-none" style={{ color: cor }}>✓</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-gray-400 italic">Nenhum item cadastrado</p>
        )}
      </div>

      {/* Rodapé */}
      <div className="bg-white border-t border-gray-100 px-5 py-3 flex gap-2">
        <button
          onClick={() => onEditar(p)}
          className="flex-1 text-sm font-medium py-2 rounded-lg text-white transition-opacity hover:opacity-85"
          style={{ backgroundColor: cor }}
        >
          Editar plano
        </button>
        <button
          onClick={() => onToggle(p.id)}
          className="px-4 py-2 rounded-lg border text-sm font-medium text-gray-500 border-gray-200 hover:bg-gray-50 transition"
        >
          {p.ativo !== false ? 'Desativar' : 'Ativar'}
        </button>
      </div>
    </div>
  )
}

export default function PlanosPage() {
  const { token } = useAuth()
  const [planos, setPlanos] = useState([])
  const [loading, setLoading] = useState(true)
  const [mostraForm, setMostraForm] = useState(false)
  const [editando, setEditando] = useState(null)
  const [form, setForm] = useState({ nome: '', descricao: '', valor: '', duracao_dias: '30' })
  const [erro, setErro] = useState('')
  const [salvando, setSalvando] = useState(false)
  const [toast, setToast] = useState(null)

  function exibirToast(msg, ok = true) {
    setToast({ msg, ok })
    setTimeout(() => setToast(null), 4000)
  }

  async function carregar(t) {
    const data = await getPlanos(t)
    setPlanos(data)
  }

  useEffect(() => {
    if (!token) return
    async function init() {
      await carregar(token)
      setLoading(false)
    }
    init()
  }, [token])

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  function iniciarEdicao(p) {
    setEditando(p.id)
    setMostraForm(false)
    setForm({ nome: p.nome, descricao: p.descricao || '', valor: p.valor, duracao_dias: p.duracao_dias })
    window.scrollTo({ top: 0, behavior: 'smooth' })
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
        exibirToast('Plano atualizado com sucesso.')
      } else {
        await criarPlano(token, body)
        exibirToast('Plano criado com sucesso.')
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
      const plano = planos.find(p => p.id === id)
      await togglePlanoAtivo(token, id)
      await carregar(token)
      exibirToast(plano?.ativo !== false ? 'Plano desativado.' : 'Plano ativado.')
    } catch (err) {
      exibirToast(err.message, false)
    }
  }

  const input = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white'
  const mostraFormulario = mostraForm || editando !== null

  return (
    <div>
      <div className="flex items-center justify-between flex-wrap gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Planos</h1>
          <p className="text-sm text-gray-500 mt-1">{planos.length} plano(s) cadastrado(s)</p>
        </div>
        {!editando && (
          <button
            onClick={() => { setMostraForm(!mostraForm); setEditando(null) }}
            className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
          >
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
          <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="col-span-2">
              <label className="text-xs text-gray-500 mb-1 block">Nome *</label>
              <input className={input} value={form.nome} onChange={e => set('nome', e.target.value)} required
                placeholder="Musculação, Natação, Crossfit..." />
            </div>
            <div className="col-span-2">
              <label className="text-xs text-gray-500 mb-1 block">
                Itens inclusos <span className="text-gray-400">(um por linha — aparecem como lista no card)</span>
              </label>
              <textarea
                rows={4}
                className={input + ' resize-none'}
                value={form.descricao}
                onChange={e => set('descricao', e.target.value)}
                placeholder={"Acesso à musculação\nAula de spinning\nAvaliação física mensal"}
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Valor mensal (R$) *</label>
              <input type="number" step="0.01" min="0.01" className={input} value={form.valor}
                onChange={e => set('valor', e.target.value)} required placeholder="99.90" />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Duração (dias) *</label>
              <input type="number" min="1" className={input} placeholder="Ex: 30" value={form.duracao_dias}
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
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {planos.map((p, i) => (
            <PlanoCard
              key={p.id}
              p={p}
              index={i}
              onEditar={iniciarEdicao}
              onToggle={toggle}
            />
          ))}
        </div>
      )}

      {toast && (
        <div className={`fixed bottom-6 left-1/2 -translate-x-1/2 px-5 py-3 rounded-xl shadow-lg text-sm font-medium text-white z-50 max-w-sm text-center transition-all ${toast.ok ? 'bg-green-500' : 'bg-red-500'}`}>
          {toast.msg}
        </div>
      )}
    </div>
  )
}
