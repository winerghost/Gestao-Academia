'use client'
import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { useAuth } from '../../../hooks/useAuth'
import { getAlunos } from '../../../lib/api'
import Paginacao from '../../../components/Paginacao'

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

const OPCOES_POR_PAGINA = [25, 50, 100, 200]

export default function AlunosPage() {
  const { token } = useAuth()
  const [alunos, setAlunos] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState('')
  const [busca, setBusca] = useState('')
  const [buscaDebounced, setBuscaDebounced] = useState('')
  const [porPagina, setPorPagina] = useState(25)
  const [pagina, setPagina] = useState(1)

  // Debounce de 400 ms na busca para não chamar o backend a cada tecla
  useEffect(() => {
    const t = setTimeout(() => setBuscaDebounced(busca), 400)
    return () => clearTimeout(t)
  }, [busca])

  // Reinicia para a primeira página sempre que filtro, busca ou tamanho mudam
  useEffect(() => { setPagina(1) }, [status, buscaDebounced, porPagina])

  const carregar = useCallback(async (paginaAtual) => {
    if (!token) return
    setLoading(true)
    const offset = (paginaAtual - 1) * porPagina
    const params = { limit: porPagina, offset }
    if (status) params.status = status
    if (buscaDebounced) params.busca = buscaDebounced

    const resp = await getAlunos(token, params)
    setAlunos(resp.data ?? [])
    setTotal(resp.total ?? 0)
    setLoading(false)
  }, [token, status, buscaDebounced, porPagina])

  useEffect(() => { carregar(pagina) }, [carregar, pagina])

  const totalPaginas = Math.max(1, Math.ceil(total / porPagina))
  const inicio = (pagina - 1) * porPagina

  return (
    <div>
      <div className="flex items-center justify-between flex-wrap gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Alunos</h1>
          <p className="text-sm text-gray-500 mt-1">{total} aluno(s) cadastrado(s)</p>
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
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white w-full sm:w-64"
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
        <label className="flex items-center gap-2 text-sm text-gray-600 sm:ml-auto">
          Registros por página
          <select
            value={porPagina}
            onChange={e => setPorPagina(Number(e.target.value))}
            className="border border-gray-200 rounded-lg px-2 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-orange-500">
            {OPCOES_POR_PAGINA.map(n => (
              <option key={n} value={n}>{n}</option>
            ))}
          </select>
        </label>
      </div>

      {/* Tabela */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <p className="text-center text-gray-400 py-12">Carregando...</p>
        ) : alunos.length === 0 ? (
          <p className="text-center text-gray-400 py-12">Nenhum aluno encontrado.</p>
        ) : (
          <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                {['Nome', 'CPF', 'Telefone', 'Status', 'Frequência', 'Ações'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {alunos.map(a => (
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
          </div>
        )}
      </div>

      {/* Paginação */}
      {!loading && total > 0 && (
        <div className="flex items-center justify-between flex-wrap gap-3 mt-4">
          <p className="text-sm text-gray-500">
            Mostrando {inicio + 1}–{Math.min(inicio + porPagina, total)} de {total} aluno(s)
          </p>
          <Paginacao pagina={pagina} totalPaginas={totalPaginas} onPagina={setPagina} />
        </div>
      )}
    </div>
  )
}
