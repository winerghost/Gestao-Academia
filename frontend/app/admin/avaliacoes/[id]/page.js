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

// ── Mapeamento corporal (silhueta + medidas posicionadas) ────────────────────
// Adaptação do "Mapeamento Corporal com Imagem": silhueta frontal com as medidas
// da avaliação ancoradas em cada parte do corpo. Alterna entre Perímetros e
// Diâmetros (como as abas da referência). SVG nativo, sem dependências/assets.
const MAPA_PERIMETROS = [
  { campo: 'circ_peito',   label: 'Peito',   lado: 'dir', x: 148, y: 142 },
  { campo: 'circ_cintura', label: 'Cintura', lado: 'dir', x: 140, y: 196 },
  { campo: 'circ_quadril', label: 'Quadril', lado: 'dir', x: 148, y: 246 },
  { campo: 'circ_braco',   label: 'Braço',   lado: 'esq', x: 62,  y: 164 },
  { campo: 'circ_coxa',    label: 'Coxa',    lado: 'esq', x: 102, y: 312 },
]

const MAPA_DIAMETROS = [
  { campo: 'diam_biacromial',           label: 'Ombros',    lado: 'dir', x: 150, y: 92 },
  { campo: 'diam_torax_transverso',     label: 'Tórax T.',  lado: 'dir', x: 146, y: 138 },
  { campo: 'diam_crista_iliaca',        label: 'Bacia',     lado: 'dir', x: 146, y: 232 },
  { campo: 'diam_bitrocanterica',       label: 'Quadril',   lado: 'dir', x: 150, y: 262 },
  { campo: 'diam_torax_ap',             label: 'Tórax AP',  lado: 'esq', x: 96,  y: 138 },
  { campo: 'diam_biepicondilo_umeral',  label: 'Cotovelo',  lado: 'esq', x: 62,  y: 200 },
  { campo: 'diam_biestiloide',          label: 'Punho',     lado: 'esq', x: 64,  y: 248 },
  { campo: 'diam_biepicondilo_femural', label: 'Joelho',    lado: 'esq', x: 106, y: 342 },
  { campo: 'diam_bimaleolar',           label: 'Tornozelo', lado: 'esq', x: 100, y: 404 },
]

// Campos de diâmetros ósseos (form de edição e card de exibição).
const DIAMETROS_CAMPOS = [
  { key: 'diam_biacromial',           label: 'Biacromial',          ph: 'Ex: 40' },
  { key: 'diam_torax_transverso',     label: 'Tórax transverso',    ph: 'Ex: 28' },
  { key: 'diam_torax_ap',             label: 'Tórax ântero-post.',  ph: 'Ex: 20' },
  { key: 'diam_biepicondilo_umeral',  label: 'Biepicôndilo umeral', ph: 'Ex: 6.5' },
  { key: 'diam_biestiloide',          label: 'Biestilóide (punho)', ph: 'Ex: 5.5' },
  { key: 'diam_crista_iliaca',        label: 'Crista ilíaca',       ph: 'Ex: 27' },
  { key: 'diam_bitrocanterica',       label: 'Bitrocantérica',      ph: 'Ex: 32' },
  { key: 'diam_biepicondilo_femural', label: 'Biepicôndilo femural', ph: 'Ex: 9.5' },
  { key: 'diam_bimaleolar',           label: 'Bimaleolar (tornozelo)', ph: 'Ex: 7' },
]

function BodyMap({ av }) {
  const [modo, setModo] = useState('perimetros') // 'perimetros' | 'diametros'
  const COR = 'var(--cor-destaque)'
  const pontos = modo === 'diametros' ? MAPA_DIAMETROS : MAPA_PERIMETROS

  return (
    <div className="bg-white rounded-xl shadow-sm p-5">
      <div className="flex items-center justify-between mb-1 flex-wrap gap-2">
        <h2 className="text-sm font-semibold text-gray-700">Mapeamento corporal</h2>
        {/* Toggle Perímetros / Diâmetros (como as abas da referência) */}
        <div className="inline-flex bg-gray-100 rounded-full p-0.5 text-xs">
          {[
            { id: 'perimetros', label: 'Perímetros' },
            { id: 'diametros',  label: 'Diâmetros' },
          ].map(t => (
            <button key={t.id} onClick={() => setModo(t.id)}
              className="px-3 py-1 rounded-full font-medium transition"
              style={modo === t.id
                ? { backgroundColor: 'white', color: '#111827', boxShadow: '0 1px 2px rgba(0,0,0,0.08)' }
                : { color: '#6b7280' }}>
              {t.label}
            </button>
          ))}
        </div>
      </div>
      <p className="text-xs text-gray-400 mb-4">
        {modo === 'diametros' ? 'Diâmetros ósseos (cm)' : 'Perímetros (cm)'} · visão anterior
      </p>

      {/* Faixa de medidas (cabeçalho, como o topo da referência) */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
        {[
          { label: 'Peso',   value: fmt(av.peso_kg, ' kg') },
          { label: 'Altura', value: fmt(av.altura_cm, ' cm') },
          { label: 'IMC',    value: fmt(av.imc) },
          { label: 'Data',   value: av.data_avaliacao || '—' },
        ].map(m => (
          <div key={m.label} className="bg-gray-50 rounded-lg px-3 py-2">
            <p className="text-[10px] uppercase tracking-wide text-gray-400">{m.label}</p>
            <p className="text-sm font-semibold text-gray-800">{m.value}</p>
          </div>
        ))}
      </div>

      <div className="flex justify-center">
        <svg viewBox="-50 0 320 430" className="w-full" style={{ maxWidth: 380 }}>
          {/* Gradiente para dar volume (sensação 3D) à silhueta */}
          <defs>
            <linearGradient id="bodyGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%"   stopColor="#eef2f6" />
              <stop offset="45%"  stopColor="#d7dee7" />
              <stop offset="100%" stopColor="#bcc7d4" />
            </linearGradient>
          </defs>

          {/* ── Silhueta ── */}
          <g fill="url(#bodyGrad)" stroke="#b3bfcd" strokeWidth="1">
            {/* Cabeça e pescoço */}
            <ellipse cx="120" cy="40" rx="22" ry="25" />
            <path d="M 111,60 C 111,72 109,76 104,80 L 136,80 C 131,76 129,72 129,60 Z" />
            {/* Tronco (ampulheta) */}
            <path d="M 90,84
                     C 78,92 84,150 100,196
                     C 90,224 92,250 104,260
                     Q 120,266 136,260
                     C 148,250 150,224 140,196
                     C 156,150 162,92 150,84
                     C 140,76 100,76 90,84 Z" />
            {/* Braços (afilando até o punho) */}
            <path d="M 88,88 C 70,96 64,170 66,236 C 66,250 58,250 56,236 C 52,168 60,98 78,86 Z" />
            <path d="M 152,88 C 170,96 176,170 174,236 C 174,250 182,250 184,236 C 188,168 180,98 162,86 Z" />
            {/* Pernas (afilando até o tornozelo) */}
            <path d="M 104,258 C 98,300 96,360 100,402 C 100,412 88,412 88,402 C 86,352 88,300 92,258 Z" />
            <path d="M 156,258 C 162,300 164,360 160,402 C 160,412 172,412 172,402 C 174,352 172,300 168,258 Z" />
            {/* Pés */}
            <ellipse cx="96"  cy="410" rx="13" ry="7" />
            <ellipse cx="164" cy="410" rx="13" ry="7" />
          </g>

          {/* ── Anotações ── */}
          {pontos.map(p => {
            const valor = av[p.campo]
            const temValor = valor != null && valor !== ''
            const gx = p.lado === 'dir' ? 202 : 18     // x do rótulo (gutter)
            const lx = p.lado === 'dir' ? 190 : 30      // x do fim da linha
            const anchor = p.lado === 'dir' ? 'start' : 'end'
            return (
              <g key={p.campo}>
                <line x1={p.x} y1={p.y} x2={lx} y2={p.y}
                  stroke={temValor ? COR : '#cbd5e1'} strokeWidth="1" strokeDasharray="2 2" />
                <circle cx={p.x} cy={p.y} r="3.5"
                  fill={temValor ? COR : '#cbd5e1'} stroke="white" strokeWidth="1.5" />
                <text x={gx} y={p.y - 2} fontSize="9" fill="#9ca3af" textAnchor={anchor}>
                  {p.label}
                </text>
                <text x={gx} y={p.y + 10} fontSize="11" fontWeight="700"
                  fill={temValor ? '#374151' : '#cbd5e1'} textAnchor={anchor}>
                  {temValor ? `${valor} cm` : '—'}
                </text>
              </g>
            )
          })}
        </svg>
      </div>
    </div>
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
    const novoForm = {
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
    }
    DIAMETROS_CAMPOS.forEach(d => { novoForm[d.key] = data[d.key] ?? '' })
    setForm(novoForm)
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
              <input className={inputCls} placeholder="Ex: 120/80" value={form.pressao_arterial}
                onChange={e => set('pressao_arterial', e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Peso (kg)</label>
              <input type="number" step="0.1" className={inputCls} placeholder="Ex: 75.5" value={form.peso_kg}
                onChange={e => set('peso_kg', e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Altura (cm)</label>
              <input type="number" step="0.1" className={inputCls} placeholder="Ex: 180" value={form.altura_cm}
                onChange={e => set('altura_cm', e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">% Gordura</label>
              <input type="number" step="0.1" className={inputCls} placeholder="Ex: 20.5" value={form.gordura_corporal}
                onChange={e => set('gordura_corporal', e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Massa magra (kg)</label>
              <input type="number" step="0.1" className={inputCls} placeholder="Ex: 60.5" value={form.massa_magra_kg}
                onChange={e => set('massa_magra_kg', e.target.value)} />
            </div>
            {[
              { key: 'circ_cintura',  label: 'Circ. Cintura (cm)', placeholder: 'Ex: 85.5' },
              { key: 'circ_quadril',  label: 'Circ. Quadril (cm)', placeholder: 'Ex: 95.0' },
              { key: 'circ_braco',    label: 'Circ. Braço (cm)', placeholder: 'Ex: 32.5' },
              { key: 'circ_coxa',     label: 'Circ. Coxa (cm)', placeholder: 'Ex: 55.0' },
              { key: 'circ_peito',    label: 'Circ. Peito (cm)', placeholder: 'Ex: 100.0' },
            ].map(({ key, label, placeholder }) => (
              <div key={key}>
                <label className="text-xs text-gray-500 mb-1 block">{label}</label>
                <input type="number" step="0.1" className={inputCls} placeholder={placeholder} value={form[key]}
                  onChange={e => set(key, e.target.value)} />
              </div>
            ))}
          </div>

          {/* Diâmetros ósseos */}
          <div>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">Diâmetros ósseos (cm)</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {DIAMETROS_CAMPOS.map(d => (
                <div key={d.key}>
                  <label className="text-xs text-gray-500 mb-1 block">{d.label}</label>
                  <input type="number" step="0.1" className={inputCls} placeholder={d.ph} value={form[d.key]}
                    onChange={e => set(d.key, e.target.value)} />
                </div>
              ))}
            </div>
          </div>

          <div>
            <label className="text-xs text-gray-500 mb-1 block">Observações</label>
            <input className={inputCls} placeholder="Digite observações relevantes sobre a avaliação..." value={form.observacoes}
              onChange={e => set('observacoes', e.target.value)} />
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
        <>
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">
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

          {/* Diâmetros ósseos */}
          <div className="bg-white rounded-xl shadow-sm p-5">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Diâmetros ósseos</h2>
            <dl>
              {DIAMETROS_CAMPOS.map(d => (
                <Campo key={d.key} label={d.label} value={fmt(av[d.key], ' cm')} />
              ))}
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

        {/* Mapeamento corporal */}
        <BodyMap av={av} />
        </>
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
