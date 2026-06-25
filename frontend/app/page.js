'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '../lib/supabase'
import { getPortalMe, getPortalMensalidades } from '../lib/api'
import NavBar from '../components/NavBar'
import MensalidadeCard from '../components/MensalidadeCard'
import StatusBadge from '../components/StatusBadge'

export default function Dashboard() {
  const router = useRouter()
  const [aluno, setAluno] = useState(null)
  const [mensalidades, setMensalidades] = useState([])
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState(null)

  useEffect(() => {
    async function carregar() {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) { router.replace('/login'); return }

      try {
        const [dadosAluno, dadosMens] = await Promise.all([
          getPortalMe(session.access_token),
          getPortalMensalidades(session.access_token),
        ])
        setAluno(dadosAluno)
        setMensalidades(dadosMens)
      } catch {
        setErro('Não foi possível carregar seus dados. Tente novamente.')
      } finally {
        setLoading(false)
      }
    }
    carregar()
  }, [router])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-400">
        Carregando...
      </div>
    )
  }

  if (erro) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-red-500 bg-red-50 px-6 py-3 rounded-lg border border-red-100">{erro}</p>
      </div>
    )
  }

  const atrasadas = mensalidades.filter(m => m.status === 'atrasada')
  const pendentes = mensalidades.filter(m => m.status === 'pendente')
  const pagas     = mensalidades.filter(m => m.status === 'paga')

  return (
    <div className="min-h-screen">
      <NavBar nomeAluno={aluno?.nome} />

      <main className="max-w-2xl mx-auto px-4 py-8 space-y-6">

        {/* Card do aluno */}
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

        {/* Alerta de atraso */}
        {atrasadas.length > 0 && (
          <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-sm text-red-700">
            <span>⚠️</span>
            <span>Você tem <strong>{atrasadas.length}</strong> mensalidade(s) em atraso.</span>
          </div>
        )}

        <Secao titulo="Em atraso" cor="text-red-600"    mensalidades={atrasadas} />
        <Secao titulo="Pendentes" cor="text-yellow-600" mensalidades={pendentes} />
        <Secao titulo="Pagas"     cor="text-green-600"  mensalidades={pagas} />

        {mensalidades.length === 0 && (
          <p className="text-center text-gray-400 py-12">Nenhuma mensalidade encontrada.</p>
        )}
      </main>
    </div>
  )
}

function Secao({ titulo, cor, mensalidades }) {
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
