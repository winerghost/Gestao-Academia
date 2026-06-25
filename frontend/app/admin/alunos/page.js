'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { supabase } from '../../../lib/supabase'
import { getAlunos } from '../../../lib/api'

const STATUS_BADGE = {
  ativo: 'bg-green-100 text-green-700',
  inativo: 'bg-gray-100 text-gray-500',
  inadimplente: 'bg-red-100 text-red-700',
}

const FILTROS = [
  { value: '', label: 'Todos' },
  { value: 'ativo', label: 'Ativos' },
  { value: 'inativo', label: 'Inativos' },
  { value: 'inadimplente', label: 'Inadimplentes' },
]

export default function AlunosPage() {
  const router = useRouter()
  const [alunos, setAlunos] = useState([])
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState('')
  const [busca, setBusca] = useState('')

  useEffect(() => {
    async function carregar() {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) { router.replace('/login'); return }
      const params = {}
      if (status) params.status = status
      const data = await getAlunos(session.access_token, params)
      setAlunos(data)
      setLoading(false)
    }
    carregar()
  }, [router, status])

  const filtrados = alunos.filter(a => {
    if (!busca) return true
    const nome = (a.profiles?.nome || '').toLowerCase()
    const cpf = (a.cpf || '').replace(/\D/g, '')
    return nome.includes(busca.toLowerCase()) || cpf.includes(busca.replace(/\D/g, ''))
  })

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Alunos</h1>
          <p className="text-sm text-gray-500 mt-1">{alunos.length} aluno(s) cadastrado(s)</p>
        </div>
        <Link href="/admin/alunos/novo"
          className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition">
          ➕ Novo aluno
        </Link>
      </div>

      {/* Filtros */}
      <div className="flex gap-3 mb-4 flex-wrap items-center">
        <input
          type="text"
          placeholder="Buscar por nome ou CPF..."
          value={busca}
          onChange={e => setBusca(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white w-64"
        />
        <div className="flex gap-2">
          {FILTROS.map(f => (
            <button key={f.value} onClick={() => setStatus(f.value)}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition
                ${status === f.value ? 'bg-orange-500 text-white' : 'bg-white border border-gray-200 text-gray-600 hover:bg-gray-50'}`}>
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tabela */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <p className="text-center text-gray-400 py-12">Carregando...</p>
        ) : filtrados.length === 0 ? (
          <p className="text-center text-gray-400 py-12">Nenhum aluno encontrado.</p>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                {['Nome', 'CPF', 'Telefone', 'Status', 'Frequência', 'Ações'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtrados.map(a => (
                <tr key={a.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-800">{a.profiles?.nome || '—'}</td>
                  <td className="px-4 py-3 text-sm text-gray-500 font-mono">{a.cpf}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{a.profiles?.telefone || '—'}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full capitalize ${STATUS_BADGE[a.status]}`}>
                      {a.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">
                    {a.frequencia_habilitada ? '✅ Sim' : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <Link href={`/admin/alunos/${a.id}`}
                      className="text-orange-500 hover:text-orange-700 text-sm font-medium">
                      Ver detalhes →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
