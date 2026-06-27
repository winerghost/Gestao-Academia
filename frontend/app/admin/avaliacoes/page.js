'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { supabase } from '../../../lib/supabase'
import { getAvaliacoes, getAlunos } from '../../../lib/api'

function imcClasse(imc) {
  if (!imc) return null
  const v = parseFloat(imc)
  if (v < 18.5) return { label: 'Abaixo do peso', cls: 'bg-blue-100 text-blue-700' }
  if (v < 25)   return { label: 'Normal',          cls: 'bg-green-100 text-green-700' }
  if (v < 30)   return { label: 'Sobrepeso',       cls: 'bg-yellow-100 text-yellow-700' }
  return             { label: 'Obesidade',          cls: 'bg-red-100 text-red-700' }
}

export default function AvaliacoesPage() {
  const router = useRouter()
  const [token,      setToken]      = useState('')
  const [avaliacoes, setAvaliacoes] = useState([])
  const [alunos,     setAlunos]     = useState([])
  const [filtroAluno, setFiltroAluno] = useState('')
  const [loading,    setLoading]    = useState(true)
  const [erro,       setErro]       = useState('')

  async function carregar(t, aluno_id = '') {
    const params = aluno_id ? { aluno_id } : {}
    const data = await getAvaliacoes(t, params)
    setAvaliacoes(data)
  }

  useEffect(() => {
    async function init() {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) { router.replace('/login'); return }
      setToken(session.access_token)
      try {
        const [, a] = await Promise.all([
          carregar(session.access_token),
          getAlunos(session.access_token),
        ])
        setAlunos(a)
      } catch (err) {
        setErro(err.message || 'Erro ao carregar avaliações.')
      } finally {
        setLoading(false)
      }
    }
    init()
  }, [router])

  async function handleFiltroAluno(e) {
    const val = e.target.value
    setFiltroAluno(val)
    await carregar(token, val)
  }

  if (loading) return <p className="text-gray-400 py-8">Carregando...</p>

  return (
    <div>
      <div className="flex items-center justify-between flex-wrap gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Avaliações Físicas</h1>
          <p className="text-sm text-gray-500 mt-1">{avaliacoes.length} avaliação(ões) encontrada(s)</p>
        </div>
        <Link
          href="/admin/avaliacoes/nova"
          className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
        >
          ➕ Nova avaliação
        </Link>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-xl shadow-sm p-4 mb-5 flex gap-4 flex-wrap items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="text-xs text-gray-500 mb-1 block">Filtrar por aluno</label>
          <select
            value={filtroAluno}
            onChange={handleFiltroAluno}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white"
          >
            <option value="">Todos os alunos</option>
            {alunos.map(a => (
              <option key={a.id} value={a.id}>{a.profiles?.nome}</option>
            ))}
          </select>
        </div>
        {filtroAluno && (
          <button
            onClick={() => { setFiltroAluno(''); carregar(token) }}
            className="text-sm text-gray-400 hover:text-gray-600 transition"
          >
            ✕ Limpar filtro
          </button>
        )}
      </div>

      {/* Tabela */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        {avaliacoes.length === 0 ? (
          <p className="text-center text-gray-400 py-12 text-sm">Nenhuma avaliação encontrada.</p>
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                {['Aluno', 'Data', 'Peso', 'Altura', 'IMC', '% Gordura', 'Massa Magra', 'Ações'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {avaliacoes.map(av => {
                const imc = imcClasse(av.imc)
                return (
                  <tr key={av.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-800">
                      {av.alunos?.profiles?.nome || '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">{av.data_avaliacao}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">
                      {av.peso_kg ? `${av.peso_kg} kg` : '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700">
                      {av.altura_cm ? `${av.altura_cm} cm` : '—'}
                    </td>
                    <td className="px-4 py-3">
                      {av.imc ? (
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${imc?.cls}`}>
                          {av.imc} {imc ? `— ${imc.label}` : ''}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700">
                      {av.gordura_corporal ? `${av.gordura_corporal}%` : '—'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-700">
                      {av.massa_magra_kg ? `${av.massa_magra_kg} kg` : '—'}
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        href={`/admin/avaliacoes/${av.id}`}
                        className="text-orange-500 hover:text-orange-700 text-xs font-medium"
                      >
                        Ver detalhes →
                      </Link>
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
