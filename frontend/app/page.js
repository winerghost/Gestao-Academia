'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '../hooks/useAuth'
import { supabase } from '../lib/supabase'
import {
  getMe,
  getPortalMe,
  getPortalMensalidades,
  getPortalFrequencias,
  getPortalAvaliacoes,
  getPortalTreino,
  getPortalAvisos,
} from '../lib/api'
import NavBar from '../components/NavBar'
import MensalidadeCard from '../components/MensalidadeCard'
import StatusBadge from '../components/StatusBadge'

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(v, suf = '') {
  return v != null ? `${v}${suf}` : '—'
}

function imcInfo(imc) {
  if (!imc) return null
  const v = parseFloat(imc)
  if (v < 18.5) return { label: 'Abaixo do peso', cls: 'text-blue-600' }
  if (v < 25)   return { label: 'Normal',          cls: 'text-green-600' }
  if (v < 30)   return { label: 'Sobrepeso',       cls: 'text-yellow-600' }
  return             { label: 'Obesidade',          cls: 'text-red-600' }
}

const AVISO_ESTILO = {
  info:    { bg: 'bg-blue-50',   borda: 'border-blue-200',   texto: 'text-blue-800',   icone: 'ℹ️' },
  aviso:   { bg: 'bg-yellow-50', borda: 'border-yellow-200', texto: 'text-yellow-800', icone: '⚠️' },
  urgente: { bg: 'bg-red-50',    borda: 'border-red-200',    texto: 'text-red-800',    icone: '🚨' },
}

// ── Componente: calendário de frequência ──────────────────────────────────────

function CalendarioFrequencia({ frequencias }) {
  const hoje    = new Date()
  const ano     = hoje.getFullYear()
  const mes     = hoje.getMonth()
  const diaHoje = hoje.getDate()

  const diasTreinados = new Set(
    frequencias
      .filter(f => {
        const d = new Date(f.data_hora)
        return d.getFullYear() === ano && d.getMonth() === mes
      })
      .map(f => new Date(f.data_hora).getDate())
  )

  const totalDias  = new Date(ano, mes + 1, 0).getDate()
  // Ajuste para semana começando na segunda (0=dom→6, 1=seg→0 ...)
  const primeiroDia = new Date(ano, mes, 1).getDay()
  const offset = (primeiroDia + 6) % 7

  const nomeMes = hoje.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })

  return (
    <div>
      <p className="text-xs text-gray-500 mb-2 capitalize">{nomeMes}</p>
      <div className="grid grid-cols-7 gap-0.5 mb-2">
        {['S', 'T', 'Q', 'Q', 'S', 'S', 'D'].map((d, i) => (
          <span key={i} className="text-center text-[10px] text-gray-400 font-semibold py-0.5">{d}</span>
        ))}
        {Array(offset).fill(null).map((_, i) => <span key={`e${i}`} />)}
        {Array.from({ length: totalDias }, (_, i) => i + 1).map(dia => (
          <div
            key={dia}
            className={`
              aspect-square flex items-center justify-center rounded-full text-[11px] font-medium
              ${diasTreinados.has(dia)
                ? 'bg-green-500 text-white'
                : dia === diaHoje
                  ? 'ring-1 ring-gray-300 text-gray-600'
                  : 'text-gray-300'
              }
            `}
          >
            {dia}
          </div>
        ))}
      </div>
      <p className="text-xs text-gray-500">
        <span className="font-semibold text-green-600">{diasTreinados.size}</span> dia(s) treinado(s) este mês
      </p>
    </div>
  )
}

// ── Componente: seção de mensalidades ─────────────────────────────────────────

function SecaoMensalidades({ titulo, cor, mensalidades }) {
  if (mensalidades.length === 0) return null
  return (
    <section>
      <h2 className={`text-xs font-semibold uppercase tracking-widest mb-3 ${cor}`}>{titulo}</h2>
      <div className="space-y-3">
        {mensalidades.map(m => <MensalidadeCard key={m.id} mensalidade={m} />)}
      </div>
    </section>
  )
}

// ── Página principal ──────────────────────────────────────────────────────────

export default function Dashboard() {
  const router = useRouter()
  const { token } = useAuth()

  const [aluno,        setAluno]        = useState(null)
  const [mensalidades, setMensalidades] = useState([])
  const [avaliacaoData, setAvaliacaoData] = useState({ avaliacoes: [], proxima_avaliacao: null })
  const [treino,       setTreino]       = useState([])
  const [frequencias,  setFrequencias]  = useState([])
  const [avisos,       setAvisos]       = useState([])
  const [loading,      setLoading]      = useState(true)
  const [erro,         setErro]         = useState(null)
  const [refreshKey,   setRefreshKey]   = useState(0)

  async function sairDaSessao() {
    await supabase.auth.signOut()
    router.replace('/login')
  }

  useEffect(() => {
    if (!token) return
    async function carregar() {
      try {
        const profile = await getMe(token)
        if (profile.tipo !== 'aluno') {
          router.replace('/admin')
          return
        }

        const [dadosAluno, dadosMens, dadosAv, dadosTreino, dadosAvisos, dadosFreq] =
          await Promise.all([
            getPortalMe(token).catch(() => null),
            getPortalMensalidades(token).catch(() => []),
            getPortalAvaliacoes(token).catch(() => ({ avaliacoes: [], proxima_avaliacao: null })),
            getPortalTreino(token).catch(() => []),
            getPortalAvisos(token).catch(() => []),
            getPortalFrequencias(token).catch(() => []),
          ])

        if (!dadosAluno) {
          setErro('Cadastro de aluno não encontrado. Entre em contato com a academia.')
          return
        }

        setAluno(dadosAluno)
        setMensalidades(dadosMens)
        setAvaliacaoData(dadosAv)
        setTreino(dadosTreino)
        setAvisos(dadosAvisos)
        setFrequencias(dadosFreq)
      } catch {
        setErro('Não foi possível carregar seus dados. Tente novamente.')
      } finally {
        setLoading(false)
      }
    }
    carregar()
  }, [token, router, refreshKey])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-400">
        Carregando...
      </div>
    )
  }

  if (erro) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="text-center max-w-sm w-full">
          <p className="text-red-500 bg-red-50 px-6 py-3 rounded-lg border border-red-100 mb-4">
            {erro}
          </p>
          <div className="flex flex-col sm:flex-row gap-2 justify-center">
            <button
              onClick={() => { setErro(null); setLoading(true); setRefreshKey(k => k + 1) }}
              className="px-4 py-2 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 transition"
            >
              Tentar novamente
            </button>
            <button
              onClick={sairDaSessao}
              className="px-4 py-2 text-sm rounded-lg bg-red-600 text-white hover:bg-red-700 transition"
            >
              Sair
            </button>
          </div>
        </div>
      </div>
    )
  }

  const atrasadas = mensalidades.filter(m => m.status === 'atrasada')
  const pendentes = mensalidades.filter(m => m.status === 'pendente')
  const pagas     = mensalidades.filter(m => m.status === 'paga')

  const ultimaAv  = avaliacaoData.avaliacoes?.[0] ?? null
  const imc       = imcInfo(ultimaAv?.imc)

  return (
    <div className="min-h-screen bg-gray-50">
      <NavBar nomeAluno={aluno?.nome} />

      <main className="max-w-2xl mx-auto px-4 py-8 space-y-5">

        {/* ── Card do aluno ── */}
        <div className="bg-white rounded-2xl shadow-sm p-6">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-800">Olá, {aluno?.nome}!</h1>
              <p className="text-sm text-gray-400 mt-1">
                {aluno?.planos?.length > 0 ? aluno.planos.join(' · ') : 'Nenhum plano ativo'}
              </p>
            </div>
            <StatusBadge status={aluno?.status ?? 'ativo'} />
          </div>
          {aluno?.frequencia_habilitada && (
            <a href="/frequencia"
               className="inline-block mt-4 text-sm text-blue-600 hover:underline font-medium">
              Ver histórico de frequência →
            </a>
          )}
        </div>

        {/* ── Avisos da academia ── */}
        {avisos.length > 0 && (
          <div className="space-y-2">
            {avisos.map(av => {
              const estilo = AVISO_ESTILO[av.tipo] ?? AVISO_ESTILO.info
              return (
                <div key={av.id}
                  className={`flex gap-3 items-start rounded-xl border px-4 py-3 ${estilo.bg} ${estilo.borda}`}>
                  <span className="text-base leading-none mt-0.5">{estilo.icone}</span>
                  <div>
                    <p className={`text-sm font-semibold ${estilo.texto}`}>{av.titulo}</p>
                    <p className={`text-sm mt-0.5 ${estilo.texto} opacity-80`}>{av.mensagem}</p>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* ── Alerta de atraso ── */}
        {atrasadas.length > 0 && (
          <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700">
            <span>⚠️</span>
            <span>Você tem <strong>{atrasadas.length}</strong> mensalidade(s) em atraso.</span>
          </div>
        )}

        {/* ── Última avaliação física ── */}
        <div className="bg-white rounded-2xl shadow-sm p-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <span>📏</span> Avaliação Física
          </h2>

          {!ultimaAv ? (
            <p className="text-sm text-gray-400">Nenhuma avaliação registrada ainda.</p>
          ) : (
            <>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs text-gray-400">
                  Última: {new Date(ultimaAv.data_avaliacao + 'T00:00:00').toLocaleDateString('pt-BR')}
                </span>
                {avaliacaoData.proxima_avaliacao && (
                  <span className="text-xs bg-orange-50 text-orange-600 border border-orange-100 px-2 py-0.5 rounded-full font-medium">
                    Próxima: {new Date(avaliacaoData.proxima_avaliacao + 'T00:00:00').toLocaleDateString('pt-BR')}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                {ultimaAv.peso_kg != null && (
                  <div className="bg-gray-50 rounded-xl p-3 text-center">
                    <p className="text-xs text-gray-400 mb-1">Peso</p>
                    <p className="text-lg font-bold text-gray-800">{ultimaAv.peso_kg}</p>
                    <p className="text-xs text-gray-400">kg</p>
                  </div>
                )}
                {ultimaAv.gordura_corporal != null && (
                  <div className="bg-gray-50 rounded-xl p-3 text-center">
                    <p className="text-xs text-gray-400 mb-1">Gordura</p>
                    <p className="text-lg font-bold text-gray-800">{ultimaAv.gordura_corporal}</p>
                    <p className="text-xs text-gray-400">%</p>
                  </div>
                )}
                {ultimaAv.massa_magra_kg != null && (
                  <div className="bg-gray-50 rounded-xl p-3 text-center">
                    <p className="text-xs text-gray-400 mb-1">Massa magra</p>
                    <p className="text-lg font-bold text-gray-800">{ultimaAv.massa_magra_kg}</p>
                    <p className="text-xs text-gray-400">kg</p>
                  </div>
                )}
                {ultimaAv.imc != null && (
                  <div className="bg-gray-50 rounded-xl p-3 text-center">
                    <p className="text-xs text-gray-400 mb-1">IMC</p>
                    <p className={`text-lg font-bold ${imc?.cls ?? 'text-gray-800'}`}>{ultimaAv.imc}</p>
                    <p className={`text-xs ${imc?.cls ?? 'text-gray-400'}`}>{imc?.label ?? '—'}</p>
                  </div>
                )}
              </div>

              {/* Medidas de circunferência */}
              {(ultimaAv.circ_cintura || ultimaAv.circ_quadril || ultimaAv.circ_braco ||
                ultimaAv.circ_coxa || ultimaAv.circ_peito) && (
                <div className="mt-3 pt-3 border-t border-gray-50">
                  <p className="text-xs text-gray-400 mb-2">Circunferências (cm)</p>
                  <div className="flex flex-wrap gap-x-4 gap-y-1">
                    {[
                      ['Cintura',  ultimaAv.circ_cintura],
                      ['Quadril',  ultimaAv.circ_quadril],
                      ['Braço',    ultimaAv.circ_braco],
                      ['Coxa',     ultimaAv.circ_coxa],
                      ['Peito',    ultimaAv.circ_peito],
                    ].filter(([, v]) => v != null).map(([label, val]) => (
                      <span key={label} className="text-xs text-gray-600">
                        <span className="text-gray-400">{label}:</span> {val} cm
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* ── Ficha de treino ── */}
        <div className="bg-white rounded-2xl shadow-sm p-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
            <span>🏋️</span> Ficha de Treino
          </h2>

          {treino.length === 0 ? (
            <p className="text-sm text-gray-400">Nenhuma ficha de treino cadastrada.</p>
          ) : (
            <div className="space-y-4">
              {treino.map(ficha => (
                <div key={ficha.id} className="border border-gray-100 rounded-xl overflow-hidden">
                  {/* Cabeçalho da ficha */}
                  <div className="bg-gray-50 px-4 py-2.5 flex items-center gap-2">
                    {ficha.divisao && (
                      <span className="w-7 h-7 rounded-lg bg-blue-600 text-white text-xs font-bold flex items-center justify-center flex-shrink-0">
                        {ficha.divisao}
                      </span>
                    )}
                    <span className="text-sm font-semibold text-gray-700">{ficha.nome}</span>
                  </div>

                  {/* Observação da ficha */}
                  {ficha.observacoes && (
                    <p className="text-xs text-gray-500 px-4 pt-2">{ficha.observacoes}</p>
                  )}

                  {/* Lista de exercícios */}
                  {ficha.exercicios_ficha?.length > 0 ? (
                    <div className="divide-y divide-gray-50">
                      {ficha.exercicios_ficha.map((ex, idx) => (
                        <div key={ex.id} className="px-4 py-2.5 flex items-start justify-between gap-2">
                          <div className="flex items-center gap-2.5 min-w-0">
                            <span className="text-xs text-gray-300 font-mono w-4 flex-shrink-0">
                              {idx + 1}
                            </span>
                            <div className="min-w-0">
                              <p className="text-sm text-gray-800 font-medium truncate">{ex.nome}</p>
                              {ex.observacoes && (
                                <p className="text-xs text-gray-400 truncate">{ex.observacoes}</p>
                              )}
                            </div>
                          </div>
                          <div className="flex items-center gap-3 flex-shrink-0 text-right">
                            {(ex.series || ex.repeticoes) && (
                              <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-md whitespace-nowrap">
                                {ex.series ? `${ex.series}×` : ''}{ex.repeticoes ?? ''}
                              </span>
                            )}
                            {ex.carga_kg && (
                              <span className="text-xs text-gray-500 whitespace-nowrap">{ex.carga_kg} kg</span>
                            )}
                            {ex.descanso_seg && (
                              <span className="text-xs text-gray-400 whitespace-nowrap">{ex.descanso_seg}s</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-gray-400 px-4 py-3">Nenhum exercício cadastrado.</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* ── Frequência do mês ── */}
        {aluno?.frequencia_habilitada && (
          <div className="bg-white rounded-2xl shadow-sm p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                <span>📅</span> Frequência do Mês
              </h2>
              <a href="/frequencia" className="text-xs text-blue-600 hover:underline font-medium">
                Ver histórico →
              </a>
            </div>
            {frequencias.length === 0 ? (
              <p className="text-sm text-gray-400">Nenhum treino registrado.</p>
            ) : (
              <CalendarioFrequencia frequencias={frequencias} />
            )}
          </div>
        )}

        {/* ── Mensalidades ── */}
        <SecaoMensalidades titulo="Em atraso" cor="text-red-600"    mensalidades={atrasadas} />
        <SecaoMensalidades titulo="Pendentes" cor="text-yellow-600" mensalidades={pendentes} />
        <SecaoMensalidades titulo="Pagas"     cor="text-green-600"  mensalidades={pagas} />

        {mensalidades.length === 0 && (
          <p className="text-center text-gray-400 py-6 text-sm">Nenhuma mensalidade encontrada.</p>
        )}

      </main>
    </div>
  )
}
