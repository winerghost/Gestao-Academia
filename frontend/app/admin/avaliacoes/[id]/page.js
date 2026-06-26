'use client'
import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import { supabase } from '../../../../lib/supabase'
import { getAvaliacao, getAvaliacoes, atualizarAvaliacao, deletarAvaliacao, downloadRelatorio } from '../../../../lib/api'

// ── Gráfico SVG nativo ────────────────────────────────────────────────────────
function LineChart({ pontos, cor = '#3c8dbc', label = '', height = 160 }) {
  const validos = pontos.filter(p => p.valor != null)
  if (validos.length < 2) {
    return (
      <div className="flex items-center justify-center h-24 text-xs text-gray-400">
        Dados insuficientes para gráfico
      </div>
    )
  }

  const W = 340, H = height
  const pad = { top: 12, right: 10, bottom: 28, left: 42 }
  const cW = W - pad.left - pad.right
  const cH = H - pad.top - pad.bottom

  const vals = validos.map(p => p.valor)
  const min  = Math.min(...vals)
  const max  = Math.max(...vals)
  const span = max - min || 1

  const px = (i) => pad.left + (i / (validos.length - 1)) * cW
  const py = (v) => pad.top  + cH - ((v - min) / span) * cH

  const pathD = validos.map((p, i) => `${i === 0 ? 'M' : 'L'}${px(i).toFixed(1)},${py(p.valor).toFixed(1)}`).join(' ')

  const yTicks = [min, (min + max) / 2, max]

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height }}>
      {/* Grid */}
      {yTicks.map((v, i) => (
        <line key={i}
          x1={pad.left} y1={py(v).toFixed(1)}
          x2={pad.left + cW} y2={py(v).toFixed(1)}
          stroke="#e5e7eb" strokeWidth="1"
        />
      ))}

      {/* Área preenchida */}
      <path
        d={`${pathD} L${px(validos.length - 1).toFixed(1)},${(pad.top + cH).toFixed(1)} L${px(0).toFixed(1)},${(pad.top + cH).toFixed(1)} Z`}
        fill={cor} fillOpacity="0.08"
      />

      {/* Linha */}
      <path d={pathD} fill="none" stroke={cor} strokeWidth="2.5" strokeLinejoin="round" />

      {/* Pontos */}
      {validos.map((p, i) => (
        <circle key={i} cx={px(i).toFixed(1)} cy={py(p.valor).toFixed(1)} r="4" fill={cor} />
      ))}

      {/* Rótulos eixo X */}
      {validos.map((p, i) => (
        <text key={i} x={px(i).toFixed(1)} y={H - 6}
          fontSize="8.5" textAnchor="middle" fill="#9ca3af"
        >
          {p.data}
        </text>
      ))}

      {/* Rótulos eixo Y */}
      {yTicks.map((v, i) => (
        <text key={i} x={pad.left - 5} y={(py(v) + 4).toFixed(1)}
          fontSize="8.5" textAnchor="end" fill="#9ca3af"
        >
          {Number(v).toFixed(1)}
        </text>
      ))}

      {/* Label */}
      {label && (
        <text x={pad.left} y={11} fontSize="9" fill={cor} fontWeight="600">{label}</text>
      )}
    </svg>
  )
}

// ── Helpers ───────────────────────────────────────────────────────────────────
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'

function imcInfo(imc) {
  if (!imc) return null
  const v = parseFloat(imc)
  if (v < 18.5) return { label: 'Abaixo do peso', cls: 'bg-blue-100 text-blue-700' }
  if (v < 25)   return { label: 'Normal',          cls: 'bg-green-100 text-green-700' }
  if (v < 30)   return { label: 'Sobrepeso',       cls: 'bg-yellow-100 text-yellow-700' }
  return             { label: 'Obesidade',          cls: 'bg-red-100 text-red-700' }
}

function fmt(v, suf = '') { return v != null ? `${v}${suf}` : '—' }

function Campo({ label, value }) {
  return (
    <div className="flex justify-between py-1.5 border-b border-gray-50 last:border-0">
      <dt className="text-sm text-gray-500">{label}</dt>
      <dd className="text-sm text-gray-800 font-medium">{value || '—'}</dd>
    </div>
  )
}

const inputCls = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white'

export default function AvaliacaoDetalhe() {
  const router     = useRouter()
  const { id }     = useParams()
  const [token,    setToken]    = useState('')
  const [av,       setAv]       = useState(null)
  const [historico, setHistorico] = useState([])
  const [editando, setEditando] = useState(false)
  const [form,     setForm]     = useState({})
  const [erro,     setErro]     = useState('')
  const [salvando, setSalvando] = useState(false)
  const [loading,  setLoading]  = useState(true)
  const [userTipo, setUserTipo] = useState('')

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  async function carregar(t) {
    const data = await getAvaliacao(t, id)
    setAv(data)
    setForm({
      instrutor_id: data.instrutor_id || '',
      data_avaliacao: data.data_avaliacao || '',
      peso_kg: data.peso_kg ?? '',
      altura_cm: data.altura_cm ?? '',
      gordura_corporal: data.gordura_corporal ?? '',
      massa_magra_kg: data.massa_magra_kg ?? '',
      circ_cintura: data.circ_cintura ?? '',
      circ_quadril: data.circ_quadril ?? '',
      circ_braco: data.circ_braco ?? '',
      circ_coxa: data.circ_coxa ?? '',
      circ_peito: data.circ_peito ?? '',
      pressao_arterial: data.pressao_arterial || '',
      observacoes: data.observacoes || '',
    })
    // Histórico do mesmo aluno (para gráficos)
    const hist = await getAvaliacoes(t, { aluno_id: data.aluno_id })
    setHistorico(hist.reverse()) // ascendente por data
  }

  useEffect(() => {
    async function init() {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) { router.replace('/login'); return }
      setToken(session.access_token)
      const res = await fetch(`${API_URL}/auth/me`, { headers: { Authorization: `Bearer ${session.access_token}` } })
      const profile = await res.json()
      setUserTipo(profile.tipo)
      await carregar(session.access_token)
      setLoading(false)
    }
    init()
  }, [router, id])

  async function salvar() {
    setSalvando(true)
    setErro('')
    try {
      await atualizarAvaliacao(token, id, form)
      await carregar(token)
      setEditando(false)
    } catch (err) {
      setErro(err.message)
    }
    setSalvando(false)
  }

  async function excluir() {
    if (!confirm('Excluir esta avaliação? Esta ação não pode ser desfeita.')) return
    try {
      await deletarAvaliacao(token, id)
      router.replace('/admin/avaliacoes')
    } catch (err) {
      alert(err.message)
    }
  }

  function baixarPDF() {
    downloadRelatorio(token, `/avaliacoes/${id}/pdf`)
  }

  if (loading) return <p className="text-gray-400 py-8">Carregando...</p>
  if (!av)     return <p className="text-red-500">Avaliação não encontrada.</p>

  const nomeAluno = av.alunos?.profiles?.nome || '—'
  const imc       = imcInfo(av.imc)

  // Prepara séries para os gráficos
  const serie = (campo) => historico.map(h => ({
    data: h.data_avaliacao?.slice(5),
    valor: h[campo] != null ? parseFloat(h[campo]) : null,
  }))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3 flex-wrap">
          <Link href="/admin/avaliacoes" className="text-sm text-gray-500 hover:text-gray-700">← Avaliações</Link>
          <span className="text-gray-300">/</span>
          <h1 className="text-2xl font-bold text-gray-800">{nomeAluno}</h1>
          <span className="text-sm text-gray-400">{av.data_avaliacao}</span>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button onClick={baixarPDF}
            className="border border-gray-200 bg-white hover:bg-gray-50 text-gray-700 px-3 py-2 rounded-lg text-sm font-medium transition">
            📄 Exportar PDF
          </button>
          {!editando && (
            <button onClick={() => setEditando(true)}
              className="border border-gray-200 bg-white hover:bg-gray-50 text-gray-700 px-3 py-2 rounded-lg text-sm font-medium transition">
              ✏️ Editar
            </button>
          )}
          {userTipo === 'admin' && (
            <button onClick={excluir}
              className="border border-red-200 bg-white hover:bg-red-50 text-red-500 px-3 py-2 rounded-lg text-sm font-medium transition">
              🗑️ Excluir
            </button>
          )}
        </div>
      </div>

      {editando ? (
        /* ── Formulário de edição ── */
        <div className="bg-white rounded-xl shadow-sm p-6 space-y-5 max-w-3xl">
          <h2 className="text-sm font-semibold text-gray-700">Editar avaliação</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Data da avaliação</label>
              <input type="date" className={inputCls} value={form.data_avaliacao}
                onChange={e => set('data_avaliacao', e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Pressão arterial</label>
              <input className={inputCls} placeholder="120/80" value={form.pressao_arterial}
                onChange={e => set('pressao_arterial', e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Peso (kg)</label>
              <input type="number" step="0.1" className={inputCls} value={form.peso_kg}
                onChange={e => set('peso_kg', e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Altura (cm)</label>
              <input type="number" step="0.1" className={inputCls} value={form.altura_cm}
                onChange={e => set('altura_cm', e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">% Gordura</label>
              <input type="number" step="0.1" className={inputCls} value={form.gordura_corporal}
                onChange={e => set('gordura_corporal', e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Massa magra (kg)</label>
              <input type="number" step="0.1" className={inputCls} value={form.massa_magra_kg}
                onChange={e => set('massa_magra_kg', e.target.value)} />
            </div>
            {[
              { key: 'circ_cintura',  label: 'Circ. Cintura (cm)' },
              { key: 'circ_quadril',  label: 'Circ. Quadril (cm)' },
              { key: 'circ_braco',    label: 'Circ. Braço (cm)' },
              { key: 'circ_coxa',     label: 'Circ. Coxa (cm)' },
              { key: 'circ_peito',    label: 'Circ. Peito (cm)' },
            ].map(({ key, label }) => (
              <div key={key}>
                <label className="text-xs text-gray-500 mb-1 block">{label}</label>
                <input type="number" step="0.1" className={inputCls} value={form[key]}
                  onChange={e => set(key, e.target.value)} />
              </div>
            ))}
            <div className="md:col-span-2">
              <label className="text-xs text-gray-500 mb-1 block">Observações</label>
              <input className={inputCls} value={form.observacoes}
                onChange={e => set('observacoes', e.target.value)} />
            </div>
          </div>

          {erro && <p className="text-sm text-red-500 bg-red-50 rounded-lg px-3 py-2">{erro}</p>}

          <div className="flex gap-3">
            <button onClick={salvar} disabled={salvando}
              className="bg-orange-500 hover:bg-orange-600 text-white px-5 py-2 rounded-lg text-sm font-medium transition disabled:opacity-60">
              {salvando ? 'Salvando...' : 'Salvar'}
            </button>
            <button onClick={() => { setEditando(false); setErro('') }}
              className="border border-gray-200 text-gray-600 px-5 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition">
              Cancelar
            </button>
          </div>
        </div>
      ) : (
        /* ── Visualização ── */
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Medidas principais */}
          <div className="bg-white rounded-xl shadow-sm p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Medidas principais</h2>
            <dl>
              <Campo label="Peso"          value={fmt(av.peso_kg, ' kg')} />
              <Campo label="Altura"        value={fmt(av.altura_cm, ' cm')} />
              <Campo label="% Gordura"     value={fmt(av.gordura_corporal, '%')} />
              <Campo label="Massa magra"   value={fmt(av.massa_magra_kg, ' kg')} />
              <Campo label="Pressão"       value={fmt(av.pressao_arterial)} />
            </dl>
            {av.imc && (
              <div className="mt-3 pt-3 border-t border-gray-50">
                <p className="text-xs text-gray-500 mb-1.5">IMC</p>
                <span className={`text-sm font-semibold px-3 py-1 rounded-full ${imc?.cls}`}>
                  {av.imc} — {imc?.label}
                </span>
              </div>
            )}
          </div>

          {/* Circunferências */}
          <div className="bg-white rounded-xl shadow-sm p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Circunferências</h2>
            <dl>
              <Campo label="Cintura" value={fmt(av.circ_cintura, ' cm')} />
              <Campo label="Quadril" value={fmt(av.circ_quadril, ' cm')} />
              <Campo label="Braço"   value={fmt(av.circ_braco,   ' cm')} />
              <Campo label="Coxa"    value={fmt(av.circ_coxa,    ' cm')} />
              <Campo label="Peito"   value={fmt(av.circ_peito,   ' cm')} />
            </dl>
          </div>

          {/* Info */}
          <div className="bg-white rounded-xl shadow-sm p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Informações</h2>
            <dl>
              <Campo label="Aluno"    value={nomeAluno} />
              <Campo label="Instrutor" value={av.instrutor_nome || '—'} />
              <Campo label="Data"     value={av.data_avaliacao} />
            </dl>
            {av.observacoes && (
              <div className="mt-3 pt-3 border-t border-gray-50">
                <p className="text-xs text-gray-500 mb-1">Observações</p>
                <p className="text-sm text-gray-700">{av.observacoes}</p>
              </div>
            )}
            <div className="mt-4">
              <Link
                href={`/admin/avaliacoes/nova?aluno_id=${av.aluno_id}`}
                className="text-xs text-orange-500 hover:text-orange-700 font-medium"
              >
                ➕ Nova avaliação para este aluno
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Gráficos de evolução */}
      {historico.length >= 2 && (
        <div className="bg-white rounded-xl shadow-sm p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">
            Evolução — {nomeAluno}
            <span className="text-xs font-normal text-gray-400 ml-2">({historico.length} avaliações)</span>
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6">
            <div>
              <p className="text-xs font-medium text-gray-500 mb-2">Peso (kg)</p>
              <LineChart pontos={serie('peso_kg')} cor="#3c8dbc" />
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 mb-2">IMC</p>
              <LineChart pontos={serie('imc')} cor="#00897b" />
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 mb-2">% Gordura</p>
              <LineChart pontos={serie('gordura_corporal')} cor="#f57c00" />
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 mb-2">Massa magra (kg)</p>
              <LineChart pontos={serie('massa_magra_kg')} cor="#6d4c8a" />
            </div>
          </div>

          {/* Circunferências */}
          <div className="mt-5 pt-5 border-t border-gray-100">
            <p className="text-xs font-semibold text-gray-500 mb-3 uppercase tracking-wide">Circunferências (cm)</p>
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-4">
              {[
                { campo: 'circ_cintura', label: 'Cintura', cor: '#e53935' },
                { campo: 'circ_quadril', label: 'Quadril', cor: '#d81b60' },
                { campo: 'circ_braco',   label: 'Braço',   cor: '#8e24aa' },
                { campo: 'circ_coxa',    label: 'Coxa',    cor: '#1e88e5' },
                { campo: 'circ_peito',   label: 'Peito',   cor: '#00acc1' },
              ].map(({ campo, label, cor }) => (
                <div key={campo}>
                  <p className="text-xs font-medium text-gray-500 mb-1">{label}</p>
                  <LineChart pontos={serie(campo)} cor={cor} height={120} />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
