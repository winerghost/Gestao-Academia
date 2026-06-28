'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useAuth } from '../../hooks/useAuth'
import { getDashboardAlunos, getDashboardFinanceiro, getDashboardFrequencia } from '../../lib/api'

function KPI({ titulo, valor, sub, cor, emoji }) {
  return (
    <div className="bg-white rounded-xl shadow-sm p-5 flex items-start justify-between">
      <div>
        <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{titulo}</p>
        <p className={`text-3xl font-bold mt-1 ${cor}`}>{valor ?? '—'}</p>
        {sub && <p className="text-xs text-gray-400 mt-1">{sub}</p>}
      </div>
      <span className="text-2xl">{emoji}</span>
    </div>
  )
}

export default function AdminDashboard() {
  // useAuth lê o token da sessão local e redireciona para /login se necessário.
  // Padrão adotado em todas as pages: obter token aqui, passar para lib/api.js.
  const { token } = useAuth()
  const [alunos, setAlunos] = useState(null)
  const [fin, setFin] = useState(null)
  const [freq, setFreq] = useState(null)
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState('')

  useEffect(() => {
    // Aguarda o token estar disponível (hook ainda não resolveu a sessão).
    if (!token) return
    async function carregar() {
      try {
        const [a, f, fr] = await Promise.all([
          getDashboardAlunos(token),
          getDashboardFinanceiro(token),
          getDashboardFrequencia(token),
        ])
        setAlunos(a)
        setFin(f)
        setFreq(fr)
      } catch (err) {
        setErro(err.message || 'Erro ao carregar dashboard.')
      } finally {
        setLoading(false)
      }
    }
    carregar()
  }, [token])

  const mesRef = fin?.mes_referencia
    ? new Date(fin.mes_referencia + '-02').toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })
    : ''

  if (loading) return <p className="text-gray-400">Carregando...</p>

  if (erro) return (
    <div className="bg-red-50 border border-red-200 rounded-xl px-6 py-4 text-red-700 text-sm">
      {erro}
    </div>
  )

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>
        <p className="text-sm text-gray-500 mt-1 capitalize">Visão geral — {mesRef}</p>
      </div>

      {/* KPIs alunos */}
      <section>
        <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-3">Alunos</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KPI titulo="Total" valor={alunos?.total} emoji="👥" cor="text-gray-800" sub={`${alunos?.novos_no_mes} novo(s) este mês`} />
          <KPI titulo="Ativos" valor={alunos?.ativos} emoji="✅" cor="text-green-600" />
          <KPI titulo="Inadimplentes" valor={alunos?.inadimplentes} emoji="⚠️" cor="text-red-500" />
          <KPI titulo="Inativos" valor={alunos?.inativos} emoji="⭕" cor="text-gray-400" />
        </div>
      </section>

      {/* KPIs financeiro */}
      <section>
        <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-3">Financeiro do mês</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KPI titulo="Receita recebida" valor={`R$ ${fin?.receita_paga?.toFixed(2)}`} emoji="💰" cor="text-green-600" sub={`${fin?.mensalidades_pagas} mensalidades`} />
          <KPI titulo="Receita prevista" valor={`R$ ${fin?.receita_prevista?.toFixed(2)}`} emoji="📅" cor="text-blue-600" sub={`${fin?.mensalidades_pendentes} pendentes`} />
          <KPI titulo="Em atraso (total)" valor={`R$ ${fin?.total_inadimplente?.toFixed(2)}`} emoji="🔴" cor="text-red-500" sub={`${fin?.mensalidades_atrasadas} no mês`} />
          <KPI titulo="Inadimplência" valor={`${fin?.taxa_inadimplencia}%`} emoji="📊" cor="text-orange-500" />
        </div>
      </section>

      {/* Frequência + Planos */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-white rounded-xl shadow-sm p-5">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-4">Frequência</h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Entradas hoje</span>
              <span className="font-bold text-gray-800">{freq?.entradas_hoje}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Entradas no mês</span>
              <span className="font-bold text-gray-800">{freq?.entradas_mes}</span>
            </div>
            <div className="flex justify-between items-center border-t pt-3">
              <span className="text-sm text-gray-600">Inativos há 7+ dias</span>
              <span className="font-bold text-orange-500">{freq?.alunos_sem_frequencia_7_dias}</span>
            </div>
          </div>
        </div>

        <div className="bg-white rounded-xl shadow-sm p-5">
          <h2 className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-4">Alunos por plano</h2>
          {!alunos?.por_plano?.length ? (
            <p className="text-sm text-gray-400">Nenhum plano ativo.</p>
          ) : (
            <div className="space-y-2">
              {alunos.por_plano.map(({ plano, total }) => (
                <div key={plano} className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">{plano}</span>
                  <span className="text-sm font-semibold text-gray-800 bg-orange-50 text-orange-600 px-2 py-0.5 rounded-full">{total}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Atalhos */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {[
          { label: 'Cadastrar aluno', href: '/admin/alunos/novo', emoji: '➕' },
          { label: 'Inadimplentes', href: '/admin/mensalidades?status=atrasada', emoji: '⚠️' },
          { label: 'Relatórios', href: '/admin/relatorios', emoji: '📄' },
          { label: 'Gerenciar planos', href: '/admin/planos', emoji: '📋' },
        ].map(({ label, href, emoji }) => (
          <Link key={href} href={href}
            className="bg-white rounded-xl shadow-sm p-4 flex items-center gap-3 hover:shadow-md transition group">
            <span className="text-xl">{emoji}</span>
            <span className="text-sm font-medium text-gray-700 group-hover:text-orange-600 transition">{label}</span>
          </Link>
        ))}
      </div>
    </div>
  )
}
