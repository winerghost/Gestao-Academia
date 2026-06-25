'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { supabase } from '../../../lib/supabase'
import { getInstrutores, criarInstrutor } from '../../../lib/api'

export default function InstrutoresPage() {
  const router = useRouter()
  const [instrutores, setInstrutores] = useState([])
  const [token, setToken] = useState('')
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
    async function init() {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) { router.replace('/login'); return }
      setToken(session.access_token)
      await carregar(session.access_token)
      setLoading(false)
    }
    init()
  }, [router])

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

  const input = "w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white"

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Instrutores</h1>
          <p className="text-sm text-gray-500 mt-1">{instrutores.length} instrutor(es) cadastrado(s)</p>
        </div>
        <button onClick={() => setMostraForm(!mostraForm)}
          className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 rounded-lg text-sm font-medium transition">
          {mostraForm ? '✕ Fechar' : '➕ Novo instrutor'}
        </button>
      </div>

      {/* Formulário */}
      {mostraForm && (
        <div className="bg-white rounded-xl shadow-sm p-5 mb-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Cadastrar novo instrutor</h2>
          <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4">
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
            {erro && <p className="col-span-2 text-sm text-red-500 bg-red-50 rounded-lg px-3 py-2">{erro}</p>}
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
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <p className="text-center text-gray-400 py-12">Carregando...</p>
        ) : instrutores.length === 0 ? (
          <p className="text-center text-gray-400 py-12">Nenhum instrutor cadastrado.</p>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                {['Nome', 'Especialidade', 'Modalidade', 'Salário', 'Admissão', 'Ações'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {instrutores.map(i => (
                <tr key={i.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm font-medium text-gray-800">{i.profiles?.nome || '—'}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{i.especialidade || '—'}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{i.modalidade || '—'}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {i.salario ? `R$ ${Number(i.salario).toFixed(2)}` : '—'}
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-500">{i.data_admissao || '—'}</td>
                  <td className="px-4 py-3">
                    <Link href={`/admin/instrutores/${i.id}`}
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
