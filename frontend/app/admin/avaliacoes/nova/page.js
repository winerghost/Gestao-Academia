'use client'
import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { supabase } from '../../../../lib/supabase'
import { getAlunos, getInstrutores, criarAvaliacao } from '../../../../lib/api'

const input = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white'

function calcImc(peso, altura) {
  if (!peso || !altura || parseFloat(altura) <= 0) return null
  const h = parseFloat(altura) / 100
  return (parseFloat(peso) / (h * h)).toFixed(2)
}

function ImcBadge({ imc }) {
  if (!imc) return null
  const v = parseFloat(imc)
  let label = '', cls = ''
  if (v < 18.5)     { label = 'Abaixo do peso'; cls = 'bg-blue-100 text-blue-700' }
  else if (v < 25)  { label = 'Normal';          cls = 'bg-green-100 text-green-700' }
  else if (v < 30)  { label = 'Sobrepeso';       cls = 'bg-yellow-100 text-yellow-700' }
  else              { label = 'Obesidade';        cls = 'bg-red-100 text-red-700' }
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cls}`}>
      IMC {imc} — {label}
    </span>
  )
}

const VAZIO = {
  aluno_id: '', instrutor_id: '', data_avaliacao: '',
  peso_kg: '', altura_cm: '', gordura_corporal: '', massa_magra_kg: '',
  circ_cintura: '', circ_quadril: '', circ_braco: '', circ_coxa: '', circ_peito: '',
  pressao_arterial: '', observacoes: '',
}

function NovaAvaliacaoForm() {
  const router      = useRouter()
  const params      = useSearchParams()
  const [token,      setToken]      = useState('')
  const [alunos,     setAlunos]     = useState([])
  const [instrutores, setInstrutores] = useState([])
  const [form,       setForm]       = useState({ ...VAZIO, aluno_id: params.get('aluno_id') || '' })
  const [erro,       setErro]       = useState('')
  const [salvando,   setSalvando]   = useState(false)
  const [loading,    setLoading]    = useState(true)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  useEffect(() => {
    async function init() {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) { router.replace('/login'); return }
      setToken(session.access_token)
      const [a, i] = await Promise.all([getAlunos(session.access_token), getInstrutores(session.access_token)])
      setAlunos(a)
      setInstrutores(i)
      setLoading(false)
    }
    init()
  }, [router])

  async function handleSubmit(e) {
    e.preventDefault()
    setSalvando(true)
    setErro('')
    const payload = Object.fromEntries(Object.entries(form).filter(([, v]) => v !== ''))
    try {
      const av = await criarAvaliacao(token, payload)
      router.replace(`/admin/avaliacoes/${av.id}`)
    } catch (err) {
      setErro(err.message)
      setSalvando(false)
    }
  }

  const imc = calcImc(form.peso_kg, form.altura_cm)

  if (loading) return <p className="text-gray-400 py-8">Carregando...</p>

  return (
    <div className="max-w-3xl">
      <div className="flex items-center gap-3 mb-6">
        <Link href="/admin/avaliacoes" className="text-sm text-gray-500 hover:text-gray-700">← Avaliações</Link>
        <span className="text-gray-300">/</span>
        <h1 className="text-2xl font-bold text-gray-800">Nova Avaliação</h1>
      </div>

      <form onSubmit={handleSubmit} className="space-y-5">

        {/* Identificação */}
        <div className="bg-white rounded-xl shadow-sm p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Identificação</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className="text-xs text-gray-500 mb-1 block">Aluno *</label>
              <select className={input} value={form.aluno_id} onChange={e => set('aluno_id', e.target.value)} required>
                <option value="">Selecione o aluno...</option>
                {alunos.map(a => (
                  <option key={a.id} value={a.id}>{a.profiles?.nome}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Instrutor responsável</label>
              <select className={input} value={form.instrutor_id} onChange={e => set('instrutor_id', e.target.value)}>
                <option value="">Sem instrutor</option>
                {instrutores.map(i => (
                  <option key={i.id} value={i.profile_id}>{i.profiles?.nome}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Data da avaliação *</label>
              <input type="date" className={input} value={form.data_avaliacao}
                onChange={e => set('data_avaliacao', e.target.value)} required />
            </div>
          </div>
        </div>

        {/* Medidas principais */}
        <div className="bg-white rounded-xl shadow-sm p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Medidas principais</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Peso (kg)</label>
              <input type="number" step="0.1" min="0" className={input} placeholder="75.0"
                value={form.peso_kg} onChange={e => set('peso_kg', e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Altura (cm)</label>
              <input type="number" step="0.1" min="0" className={input} placeholder="175.0"
                value={form.altura_cm} onChange={e => set('altura_cm', e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">% Gordura corporal</label>
              <input type="number" step="0.1" min="0" max="100" className={input} placeholder="18.5"
                value={form.gordura_corporal} onChange={e => set('gordura_corporal', e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Massa magra (kg)</label>
              <input type="number" step="0.1" min="0" className={input} placeholder="61.0"
                value={form.massa_magra_kg} onChange={e => set('massa_magra_kg', e.target.value)} />
            </div>
          </div>
          {imc && (
            <div className="mt-3">
              <ImcBadge imc={imc} />
            </div>
          )}
        </div>

        {/* Circunferências */}
        <div className="bg-white rounded-xl shadow-sm p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Circunferências (cm)</h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            {[
              { key: 'circ_cintura',  label: 'Cintura' },
              { key: 'circ_quadril',  label: 'Quadril' },
              { key: 'circ_braco',    label: 'Braço' },
              { key: 'circ_coxa',     label: 'Coxa' },
              { key: 'circ_peito',    label: 'Peito' },
            ].map(({ key, label }) => (
              <div key={key}>
                <label className="text-xs text-gray-500 mb-1 block">{label}</label>
                <input type="number" step="0.1" min="0" className={input} placeholder="—"
                  value={form[key]} onChange={e => set(key, e.target.value)} />
              </div>
            ))}
          </div>
        </div>

        {/* Outros */}
        <div className="bg-white rounded-xl shadow-sm p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Outros</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Pressão arterial</label>
              <input className={input} placeholder="120/80"
                value={form.pressao_arterial} onChange={e => set('pressao_arterial', e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Observações</label>
              <input className={input} placeholder="Observações gerais..."
                value={form.observacoes} onChange={e => set('observacoes', e.target.value)} />
            </div>
          </div>
        </div>

        {erro && (
          <p className="text-sm text-red-500 bg-red-50 border border-red-100 rounded-lg px-4 py-2">{erro}</p>
        )}

        <div className="flex gap-3">
          <button type="submit" disabled={salvando}
            className="bg-orange-500 hover:bg-orange-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition disabled:opacity-60">
            {salvando ? 'Salvando...' : 'Salvar avaliação'}
          </button>
          <Link href="/admin/avaliacoes"
            className="border border-gray-200 text-gray-600 px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-gray-50 transition">
            Cancelar
          </Link>
        </div>
      </form>
    </div>
  )
}

// useSearchParams() exige um boundary de Suspense para o build de produção
// conseguir pré-renderizar a página.
export default function NovaAvaliacaoPage() {
  return (
    <Suspense fallback={<p className="text-gray-400 py-8">Carregando...</p>}>
      <NovaAvaliacaoForm />
    </Suspense>
  )
}
