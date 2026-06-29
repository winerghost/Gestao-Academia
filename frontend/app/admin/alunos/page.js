'use client'
import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { useAuth } from '../../../hooks/useAuth'
import { getAlunos } from '../../../lib/api'
import Paginacao from '../../../components/Paginacao'
import TabelaShell, { TH, TD, BTN_ICON } from '../../../components/TabelaShell'
import { IcoOlho } from '../../../components/IcoAcoes'

const STATUS_BADGE = {
  ativo:        'bg-green-50 text-green-700',
  inativo:      'bg-gray-100 text-gray-500',
  inadimplente: 'bg-red-50 text-red-600',
}

const FILTROS = [
  { value: '', label: 'Todos' },
  { value: 'ativo', label: 'Ativos' },
  { value: 'inativo', label: 'Inativos' },
  { value: 'inadimplente', label: 'Inadimplentes' },
]

const OPCOES_POR_PAGINA = [25, 50, 100, 200]

const COLUNAS = ['Nome', 'CPF', 'Telefone', 'Status', 'Frequência', 'Ações']

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

  useEffect(() => {
    const t = setTimeout(() => setBuscaDebounced(busca), 400)
    return () => clearTimeout(t)
  }, [busca])

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
      {/* Cabeçalho */}
      <div className="flex items-center justify-between flex-wrap gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Alunos</h1>
          <p className="text-sm text-gray-400 mt-0.5">{total} aluno(s) cadastrado(s)</p>
        </div>
        <Link href="/admin/alunos/novo"
          className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition">
          + Novo aluno
        </Link>
      </div>

      {/* Filtros */}
      <div className="flex gap-2 mb-4 flex-wrap items-center">
        <input
          type="text"
          placeholder="Buscar por nome ou CPF..."
          value={busca}
          onChange={e => setBusca(e.target.value)}
          className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400 bg-white w-full sm:w-64"
        />
        <div className="flex gap-1.5">
          {FILTROS.map(f => (
            <button key={f.value} onClick={() => setStatus(f.value)}
              className={`px-3 py-2 rounded-lg text-sm font-medium transition
                ${status === f.value
                  ? 'bg-orange-500 text-white'
                  : 'bg-white border border-gray-200 text-gray-500 hover:bg-gray-50'}`}>
              {f.label}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-sm text-gray-500 ml-auto">
          Por página
          <select value={porPagina} onChange={e => setPorPagina(Number(e.target.value))}
            className="border border-gray-200 rounded-lg px-2 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-orange-400">
            {OPCOES_POR_PAGINA.map(n => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
      </div>

      {/* Tabela */}
      <TabelaShell loading={loading} vazio={alunos.length === 0 && 'Nenhum aluno encontrado.'}>
        <thead className="bg-gray-50 border-b border-gray-100">
          <tr>
            {COLUNAS.map(h => <th key={h} className={TH}>{h}</th>)}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {alunos.map(a => (
            <tr key={a.id} className="hover:bg-gray-50/60 transition-colors">
              <td className={`${TD} font-medium text-gray-800`}>{a.profiles?.nome || '—'}</td>
              <td className={`${TD} text-gray-500 font-mono tracking-wide`}>{a.cpf}</td>
              <td className={`${TD} text-gray-500`}>{a.profiles?.telefone || '—'}</td>
              <td className={TD}>
                <span className={`inline-flex items-center text-xs font-semibold px-2.5 py-0.5 rounded-full capitalize ${STATUS_BADGE[a.status] ?? 'bg-gray-100 text-gray-500'}`}>
                  {a.status}
                </span>
              </td>
              <td className={`${TD} text-gray-500`}>
                {a.frequencia_habilitada
                  ? <span className="inline-flex items-center text-xs font-semibold px-2.5 py-0.5 rounded-full bg-blue-50 text-blue-600">Ativada</span>
                  : '—'}
              </td>
              <td className={TD}>
                <Link href={`/admin/alunos/${a.id}`}
                  className={BTN_ICON + ' inline-flex items-center'} title="Ver detalhes">
                  <IcoOlho />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </TabelaShell>

      {/* Paginação */}
      {!loading && total > 0 && (
        <div className="flex items-center justify-between flex-wrap gap-3 mt-4">
          <p className="text-sm text-gray-400">
            Mostrando {inicio + 1}–{Math.min(inicio + porPagina, total)} de {total} aluno(s)
          </p>
          <Paginacao pagina={pagina} totalPaginas={totalPaginas} onPagina={setPagina} />
        </div>
      )}
    </div>
  )
}
