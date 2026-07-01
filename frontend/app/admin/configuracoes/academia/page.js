'use client'
import { useEffect, useState, useRef } from 'react'
import Link from 'next/link'
import { useAuth } from '../../../../hooks/useAuth'
import { getConfigAcademia, atualizarConfigAcademia } from '../../../../lib/api'
import { mascaraTelefone } from '../../../../lib/masks'

const input = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2'
const ring = { '--tw-ring-color': 'var(--cor-destaque)' }
const btn = 'text-white px-5 py-2 rounded-lg text-sm font-medium transition disabled:opacity-60'
const btnStyle = { backgroundColor: 'var(--cor-destaque)' }

const DIAS = [
  ['seg', 'Segunda'], ['ter', 'Terça'], ['qua', 'Quarta'], ['qui', 'Quinta'],
  ['sex', 'Sexta'], ['sab', 'Sábado'], ['dom', 'Domingo'],
]

function horarioPadrao() {
  return { abre: '06:00', fecha: '22:00', fechado: false }
}

const PERMS_LABELS = [
  {
    key: 'relatorio_financeiro',
    label: 'Relatório financeiro',
    desc: 'Mensalidades, pagamentos e juros do mês',
  },
  {
    key: 'relatorio_inadimplencia',
    label: 'Relatório de inadimplência',
    desc: 'Alunos com mensalidades atrasadas',
  },
]

export default function AcademiaPage() {
  const { token } = useAuth()
  const [loading, setLoading] = useState(true)
  const [salvando, setSalvando] = useState(false)
  const [toast, setToast] = useState(null)   // { msg, ok }
  const [toastVisivel, setToastVisivel] = useState(false)
  const toastTimer = useRef(null)

  function exibirToast(msg, ok = true) {
    clearTimeout(toastTimer.current)
    setToast({ msg, ok })
    // pequeno delay para o CSS de entrada rodar
    setTimeout(() => setToastVisivel(true), 10)
    toastTimer.current = setTimeout(() => {
      setToastVisivel(false)
      setTimeout(() => setToast(null), 300) // aguarda animação de saída
    }, 4000)
  }

  const [dados, setDados] = useState({ nome: '', cnpj: '', telefone: '', email: '', endereco: '' })
  const [horarios, setHorarios] = useState(() =>
    Object.fromEntries(DIAS.map(([k]) => [k, horarioPadrao()]))
  )
  const [permissoesRecep, setPermissoesRecep] = useState({
    relatorio_financeiro: false,
    relatorio_inadimplencia: false,
  })

  useEffect(() => {
    if (!token) return
    async function init() {
      try {
        const c = await getConfigAcademia(token)
        setDados({
          nome: c.nome || '', cnpj: c.cnpj || '', telefone: c.telefone || '',
          email: c.email || '', endereco: c.endereco || '',
        })
        setHorarios(prev => {
          const merged = { ...prev }
          for (const [k] of DIAS) {
            if (c.horarios && c.horarios[k]) merged[k] = { ...horarioPadrao(), ...c.horarios[k] }
          }
          return merged
        })
        if (c.permissoes_recepcionista) {
          setPermissoesRecep({
            relatorio_financeiro: c.permissoes_recepcionista.relatorio_financeiro ?? false,
            relatorio_inadimplencia: c.permissoes_recepcionista.relatorio_inadimplencia ?? false,
          })
        }
      } catch (err) {
        exibirToast(err.message, false)
      }
      setLoading(false)
    }
    init()
  }, [token])

  function setDia(dia, campo, valor) {
    setHorarios(h => ({ ...h, [dia]: { ...h[dia], [campo]: valor } }))
  }

  async function salvar(e) {
    e.preventDefault()
    setSalvando(true)
    try {
      await atualizarConfigAcademia(token, {
        ...dados,
        horarios,
        permissoes_recepcionista: permissoesRecep,
      })
      exibirToast('Configurações da academia salvas.')
    } catch (err) {
      exibirToast(err.message, false)
    }
    setSalvando(false)
  }

  if (loading) return <p className="text-gray-400">Carregando...</p>

  return (
    <div className="max-w-3xl">
      <Link href="/admin/configuracoes" className="text-sm text-gray-500 hover:text-gray-700">
        ‹ Voltar para Configurações
      </Link>
      <h1 className="text-2xl font-bold text-gray-800 mt-2 mb-6">Academia</h1>

      <form onSubmit={salvar}>
        {/* Dados cadastrais */}
        <div className="bg-white rounded-xl shadow-sm p-5 mb-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Dados cadastrais</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="text-xs text-gray-500 mb-1 block">Nome da academia</label>
              <input className={input} style={ring} placeholder="Ex: Academia Fitness Pro" value={dados.nome}
                onChange={e => setDados(d => ({ ...d, nome: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">CNPJ</label>
              <input className={input} style={ring} value={dados.cnpj} placeholder="00.000.000/0000-00"
                onChange={e => setDados(d => ({ ...d, cnpj: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Telefone</label>
              <input className={input} style={ring} value={dados.telefone} placeholder="(11) 3333-4444"
                onChange={e => setDados(d => ({ ...d, telefone: mascaraTelefone(e.target.value) }))} maxLength="15" />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">E-mail de contato</label>
              <input type="email" className={input} style={ring} placeholder="contato@academia.com" value={dados.email}
                onChange={e => setDados(d => ({ ...d, email: e.target.value }))} />
            </div>
            <div className="sm:col-span-2">
              <label className="text-xs text-gray-500 mb-1 block">Endereço</label>
              <input className={input} style={ring} placeholder="Rua, número, bairro, cidade, CEP" value={dados.endereco}
                onChange={e => setDados(d => ({ ...d, endereco: e.target.value }))} />
            </div>
          </div>
        </div>

        {/* Horários */}
        <div className="bg-white rounded-xl shadow-sm p-5 mb-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Horários de funcionamento</h2>
          <div className="space-y-2">
            {DIAS.map(([k, label]) => {
              const dia = horarios[k]
              return (
                <div key={k} className="flex items-center gap-3 flex-wrap">
                  <span className="w-20 text-sm text-gray-600">{label}</span>
                  <label className="flex items-center gap-1.5 text-xs text-gray-500 select-none">
                    <input type="checkbox" checked={dia.fechado}
                      onChange={e => setDia(k, 'fechado', e.target.checked)} />
                    Fechado
                  </label>
                  {!dia.fechado && (
                    <div className="flex items-center gap-2">
                      <input type="time" className="border border-gray-200 rounded-lg px-2 py-1 text-sm"
                        value={dia.abre || ''} onChange={e => setDia(k, 'abre', e.target.value)} />
                      <span className="text-gray-400 text-sm">às</span>
                      <input type="time" className="border border-gray-200 rounded-lg px-2 py-1 text-sm"
                        value={dia.fecha || ''} onChange={e => setDia(k, 'fecha', e.target.value)} />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Permissões da Recepcionista */}
        <div className="bg-white rounded-xl shadow-sm p-5 mb-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-1">Permissões — Recepcionista</h2>
          <p className="text-xs text-gray-400 mb-4">
            Relatórios financeiros são restritos ao Administrador por padrão.
            Habilite abaixo para liberar o acesso ao cargo Recepcionista.
          </p>
          <div className="space-y-3">
            {PERMS_LABELS.map(({ key, label, desc }) => (
              <label key={key} className="flex items-start gap-3 cursor-pointer group">
                <input
                  type="checkbox"
                  checked={permissoesRecep[key] || false}
                  onChange={e => setPermissoesRecep(p => ({ ...p, [key]: e.target.checked }))}
                  className="mt-0.5 accent-orange-500 w-4 h-4 flex-shrink-0"
                />
                <div>
                  <p className="text-sm font-medium text-gray-700 group-hover:text-gray-900 transition">{label}</p>
                  <p className="text-xs text-gray-400">{desc}</p>
                </div>
              </label>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button type="submit" className={btn} style={btnStyle} disabled={salvando}>
            {salvando ? 'Salvando...' : 'Salvar alterações'}
          </button>
        </div>
      </form>

      {/* Toast topo-direito com slide-in da direita */}
      {toast && (
        <div
          className={`fixed top-5 right-5 z-50 flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg text-sm font-medium text-white max-w-xs transition-all duration-300 ${
            toast.ok ? 'bg-green-500' : 'bg-red-500'
          } ${toastVisivel ? 'opacity-100 translate-x-0' : 'opacity-0 translate-x-8'}`}
        >
          <span>{toast.ok ? '✓' : '✕'}</span>
          <span>{toast.msg}</span>
        </div>
      )}
    </div>
  )
}
