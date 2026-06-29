'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useAuth } from '../../../hooks/useAuth'
import { getInstrutores, criarInstrutor } from '../../../lib/api'
import TabelaShell, { TH, TD, BTN_ICON } from '../../../components/TabelaShell'
import { IcoOlho } from '../../../components/IcoAcoes'

const COLUNAS = ['Nome', 'Especialidade', 'Modalidade', 'Salário', 'Admissão', 'Ações']

function fmtData(s) {
  if (!s) return '—'
  const [ano, mes, dia] = s.split('-')
  return `${dia}/${mes}/${ano}`
}

export default function InstrutoresPage() {
  const { token } = useAuth()
  const [instrutores, setInstrutores] = useState([])
  const [loading, setLoading] = useState(true)
  const [mostraForm, setMostraForm] = useState(false)
  const [form, setForm] = useState({ nome: '', email: '', senha: '', especialidade: '', modalidade: '', salario: '', data_admissao: '' })
  const [erro, setErro] = useState('')
  const [salvando, setSalvando] = useState(false)

  async function carregar(t) {
    const data = await getInstrutores(t)
    setInstrutores(data)
  }

  useEffect(() => {
    if (!token) return
    async function init() {
      await carregar(token)
      setLoading(false)
    }
    init()
  }, [token])

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  async function handleSubmit(e) {
    e.preventDefault()
    setSalvando(true)
    setErro('')
    try {
      await criarInstrutor(token, {
        ...form,
        salario: form.salario ? parseFloat(form.salario) : undefined,
      })
      setForm({ nome: '', email: '', senha: '', especialidade: '', modalidade: '', salario: '', data_admissao: '' })
      setMostraForm(false)
      await carregar(token)
    } catch (err) {
      setErro(err.message)
    }
    setSalvando(false)
  }

  const input = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-400 bg-white'

  return (
    <div>
      {/* Cabeçalho */}
      <div className="flex items-center justify-between flex-wrap gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Instrutores</h1>
          <p className="text-sm text-gray-400 mt-0.5">{instrutores.length} instrutor(es) cadastrado(s)</p>
        </div>
        <button onClick={() => setMostraForm(!mostraForm)}
          className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition">
          {mostraForm ? '✕ Fechar' : '+ Novo instrutor'}
        </button>
      </div>

      {/* Formulário */}
      {mostraForm && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 mb-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Cadastrar novo instrutor</h2>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Nome *</label>
              <input className={input} value={form.nome} onChange={e => set('nome', e.target.value)} required placeholder="Maria Santos" />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">E-mail *</label>
              <input type="email" className={input} value={form.email} onChange={e => set('email', e.target.value)} required placeholder="maria@academia.com" />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Senha *</label>
              <input type="password" className={input} value={form.senha} onChange={e => set('senha', e.target.value)} required placeholder="Mínimo 6 caracteres" />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Especialidade</label>
              <input className={input} value={form.especialidade} onChange={e => set('especialidade', e.target.value)} placeholder="Musculação, Natação..." />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Modalidade</label>
              <input className={input} value={form.modalidade} onChange={e => set('modalidade', e.target.value)} placeholder="Personal, Turma..." />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Salário (R$)</label>
              <input type="number" step="0.01" min="0" className={input} value={form.salario} onChange={e => set('salario', e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Data de admissão</label>
              <input type="date" className={input} value={form.data_admissao} onChange={e => set('data_admissao', e.target.value)} />
            </div>
            {erro && <p className="col-span-2 text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{erro}</p>}
            <div className="col-span-2 flex gap-3">
              <button type="submit" disabled={salvando}
                className="bg-orange-500 hover:bg-orange-600 text-white px-5 py-2 rounded-lg text-sm font-medium transition disabled:opacity-60">
                {salvando ? 'Cadastrando...' : 'Cadastrar instrutor'}
              </button>
              <button type="button" onClick={() => setMostraForm(false)}
                className="border border-gray-200 text-gray-600 px-5 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 transition">
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Tabela */}
      <TabelaShell loading={loading} vazio={instrutores.length === 0 && 'Nenhum instrutor cadastrado.'}>
        <thead className="bg-gray-50 border-b border-gray-100">
          <tr>
            {COLUNAS.map(h => <th key={h} className={TH}>{h}</th>)}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {instrutores.map(i => (
            <tr key={i.id} className="hover:bg-gray-50/60 transition-colors">
              <td className={`${TD} font-medium text-gray-800`}>{i.profiles?.nome || '—'}</td>
              <td className={`${TD} text-gray-500`}>{i.especialidade || '—'}</td>
              <td className={`${TD} text-gray-500`}>{i.modalidade || '—'}</td>
              <td className={`${TD} text-gray-700`}>
                {i.salario ? `R$ ${Number(i.salario).toLocaleString('pt-BR', { minimumFractionDigits: 2 })}` : '—'}
              </td>
              <td className={`${TD} text-gray-500`}>{fmtData(i.data_admissao)}</td>
              <td className={TD}>
                <Link href={`/admin/instrutores/${i.id}`}
                  className={`${BTN_ICON} inline-flex items-center`} title="Ver detalhes">
                  <IcoOlho />
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </TabelaShell>
    </div>
  )
}
