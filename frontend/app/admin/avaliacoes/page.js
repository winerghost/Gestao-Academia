'use client'
import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { useAuth } from '../../../hooks/useAuth'
import { getAvaliacoes, getAlunos } from '../../../lib/api'
import Paginacao from '../../../components/Paginacao'
import TabelaShell, { TH, TD, BTN_ICON } from '../../../components/TabelaShell'
import { IcoOlho } from '../../../components/IcoAcoes'

function imcClasse(imc) {
  if (!imc) return null
  const v = parseFloat(imc)
  if (v < 18.5) return { label: 'Abaixo do peso', cls: 'bg-blue-50 text-blue-600' }
  if (v < 25)   return { label: 'Normal',          cls: 'bg-green-50 text-green-700' }
  if (v < 30)   return { label: 'Sobrepeso',       cls: 'bg-yellow-50 text-yellow-700' }
  return             { label: 'Obesidade',          cls: 'bg-red-50 text-red-600' }
}

function fmtData(s) {
  if (!s) return '—'
  const [ano, mes, dia] = s.split('-')
  return `${dia}/${mes}/${ano}`
}

const OPCOES_POR_PAGINA = [10, 25, 50]

const COLUNAS = ['Aluno', 'Data', 'Peso', 'Altura', 'IMC', '% Gordura', 'Massa Magra', 'Ações']

export default function AvaliacoesPage() {
  const { token } = useAuth()
  const [avaliacoes,     setAvaliacoes]     = useState([])
  const [alunos,         setAlunos]         = useState([])
  const [total,          setTotal]          = useState(0)
  const [loading,        setLoading]        = useState(true)
  const [filtroAluno,    setFiltroAluno]    = useState('')
  const [buscaNome,      setBuscaNome]      = useState('')
  const [buscaDebounced, setBuscaDebounced] = useState('')
  const [porPagina,      setPorPagina]      = useState(25)
  const [pagina,         setPagina]         = useState(1)

  useEffect(() => {
    if (!token) return
    getAlunos(token, { limit: 200 })
      .then(resp => setAlunos(resp.data ?? []))
      .catch(() => {})
  }, [token])

  useEffect(() => {
    const t = setTimeout(() => setBuscaDebounced(buscaNome), 400)
    return () => clearTimeout(t)
  }, [buscaNome])

  useEffect(() => { setPagina(1) }, [filtroAluno, buscaDebounced, porPagina])

  const carregar = useCallback(async (paginaAtual) => {
    if (!token) return
    setLoading(true)
    const offset = (paginaAtual - 1) * porPagina
    const params = { limit: porPagina, offset }
    if (filtroAluno)    params.aluno_id = filtroAluno
    if (buscaDebounced) params.busca    = buscaDebounced
    const resp = await getAvaliacoes(token, params)
    setAvaliacoes(resp.data ?? [])
    setTotal(resp.total ?? 0)
    setLoading(false)
  }, [token, filtroAluno, buscaDebounced, porPagina])

  useEffect(() => { carregar(pagina) }, [carregar, pagina])

  const totalPaginas = Math.max(1, Math.ceil(total / porPagina))
  const inicio = (pagina - 1) * porPagina

  return (
    <div>
      {/* Cabeçalho */}
      <div className="flex items-center justify-between flex-wrap gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Avaliações Físicas</h1>
          <p className="text-sm text-gray-400 mt-0.5">{total} avaliação(ões) encontrada(s)</p>
        </div>
        <Link href="/admin/avaliacoes/nova"
          className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition">
          + Nova avaliação
        </Link>
      </div>

      {/* Filtros */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-4 mb-5 flex gap-4 flex-wrap items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="text-xs text-gray-400 mb-1 block">Pesquisar por nome</label>
          <input
            type="text"
            value={buscaNome}
            onChange={e => setBuscaNome(e.target.value)}
            placeholder="Pesquisar por nome do aluno..."
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400 bg-white"
          />
        </div>
        <div className="flex-1 min-w-[200px]">
          <label className="text-xs text-gray-400 mb-1 block">Filtrar por aluno</label>
          <select
            value={filtroAluno}
            onChange={e => setFiltroAluno(e.target.value)}
            autoComplete="off"
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400 bg-white"
          >
            <option value="">Todos os alunos</option>
            {alunos.map(a => (
              <option key={a.id} value={a.id}>{a.profiles?.nome}</option>
            ))}
          </select>
        </div>
        {filtroAluno && (
          <button
            onClick={() => setFiltroAluno('')}
            className="text-sm text-gray-400 hover:text-gray-600 transition self-end pb-2"
          >
            ✕ Limpar filtro
          </button>
        )}
        <label className="flex items-center gap-2 text-sm text-gray-500 sm:ml-auto">
          Por página
          <select
            value={porPagina}
            onChange={e => setPorPagina(Number(e.target.value))}
            className="border border-gray-200 rounded-lg px-2 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-orange-400"
          >
            {OPCOES_POR_PAGINA.map(n => <option key={n} value={n}>{n}</option>)}
          </select>
        </label>
      </div>

      {/* Tabela */}
      <TabelaShell loading={loading} vazio={avaliacoes.length === 0 && 'Nenhuma avaliação encontrada.'}>
        <thead className="bg-gray-50 border-b border-gray-100">
          <tr>
            {COLUNAS.map(h => <th key={h} className={TH}>{h}</th>)}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {avaliacoes.map(av => {
            const imc = imcClasse(av.imc)
            return (
              <tr key={av.id} className="hover:bg-gray-50/60 transition-colors">
                <td className={`${TD} font-medium text-gray-800`}>
                  {av.alunos?.profiles?.nome || '—'}
                </td>
                <td className={`${TD} text-gray-500`}>{fmtData(av.data_avaliacao)}</td>
                <td className={`${TD} text-gray-700`}>
                  {av.peso_kg ? `${av.peso_kg} kg` : '—'}
                </td>
                <td className={`${TD} text-gray-700`}>
                  {av.altura_cm ? `${av.altura_cm} cm` : '—'}
                </td>
                <td className={TD}>
                  {av.imc ? (
                    <span className={`inline-flex items-center text-xs font-semibold px-2.5 py-0.5 rounded-full ${imc?.cls}`}>
                      {av.imc} — {imc?.label}
                    </span>
                  ) : '—'}
                </td>
                <td className={`${TD} text-gray-700`}>
                  {av.gordura_corporal ? `${av.gordura_corporal}%` : '—'}
                </td>
                <td className={`${TD} text-gray-700`}>
                  {av.massa_magra_kg ? `${av.massa_magra_kg} kg` : '—'}
                </td>
                <td className={TD}>
                  <Link href={`/admin/avaliacoes/${av.id}`}
                    className={`${BTN_ICON} inline-flex items-center`} title="Ver detalhes">
                    <IcoOlho />
                  </Link>
                </td>
              </tr>
            )
          })}
        </tbody>
      </TabelaShell>

      {/* Paginação */}
      {!loading && total > 0 && (
        <div className="flex items-center justify-between flex-wrap gap-3 mt-4">
          <p className="text-sm text-gray-400">
            Mostrando {inicio + 1}–{Math.min(inicio + porPagina, total)} de {total} avaliação(ões)
          </p>
          <Paginacao pagina={pagina} totalPaginas={totalPaginas} onPagina={setPagina} />
        </div>
      )}
    </div>
  )
}
