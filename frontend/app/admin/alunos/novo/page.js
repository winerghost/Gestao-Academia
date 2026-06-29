'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '../../../../hooks/useAuth'
import { criarAluno } from '../../../../lib/api'
import CapturaFoto from '@/components/CapturaFoto'

export default function NovoAluno() {
  const router = useRouter()
  const { token } = useAuth()
  const [form, setForm] = useState({
    nome: '', email: '', senha: '', cpf: '', telefone: '',
    data_nascimento: '', endereco: '', status: 'ativo',
    frequencia_habilitada: false, foto: null,
  })
  const [erro, setErro] = useState('')
  const [loading, setLoading] = useState(false)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  async function handleSubmit(e) {
    e.preventDefault()
    setErro('')
    setLoading(true)
    try {
      await criarAluno(token, form)
      router.push('/admin/alunos')
    } catch (err) {
      setErro(err.message)
    }
    setLoading(false)
  }

  const input = "w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent bg-white"

  return (
    <div>
      <div className="flex items-center gap-2 mb-6 text-sm text-gray-500">
        <Link href="/admin/alunos" className="hover:text-gray-700">Alunos</Link>
        <span>/</span>
        <span className="text-gray-800 font-medium">Novo aluno</span>
      </div>

      <h1 className="text-2xl font-bold text-gray-800 mb-6">Cadastrar novo aluno</h1>

      <div className="bg-white rounded-xl shadow-sm p-6 max-w-2xl">
        <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4">
          <div className="col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-2">Foto do aluno</label>
            <CapturaFoto value={form.foto} nome={form.nome} onChange={d => set('foto', d)} disabled={loading} />
            <p className="text-xs text-gray-400 mt-2">
              Se o e-mail do aluno tiver um Gravatar, ele será usado no lugar desta foto.
            </p>
          </div>
          <div className="col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">Nome completo *</label>
            <input className={input} value={form.nome} onChange={e => set('nome', e.target.value)} required placeholder="João da Silva" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">E-mail *</label>
            <input type="email" className={input} value={form.email} onChange={e => set('email', e.target.value)} required placeholder="joao@email.com" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Senha *</label>
            <input type="password" className={input} value={form.senha} onChange={e => set('senha', e.target.value)} required placeholder="Mínimo 6 caracteres" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">CPF *</label>
            <input className={input} value={form.cpf} onChange={e => set('cpf', e.target.value)} required placeholder="000.000.000-00" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Telefone</label>
            <input className={input} value={form.telefone} onChange={e => set('telefone', e.target.value)} placeholder="(11) 99999-9999" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Data de nascimento</label>
            <input type="date" className={input} value={form.data_nascimento} onChange={e => set('data_nascimento', e.target.value)} />
          </div>
          <div className="col-span-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">Endereço</label>
            <input className={input} value={form.endereco} onChange={e => set('endereco', e.target.value)} placeholder="Rua, número, bairro, cidade" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select className={input} value={form.status} onChange={e => set('status', e.target.value)}>
              <option value="ativo">Ativo</option>
              <option value="inativo">Inativo</option>
            </select>
          </div>
          <div className="flex items-center gap-3 pt-6">
            <input type="checkbox" id="freq" checked={form.frequencia_habilitada}
              onChange={e => set('frequencia_habilitada', e.target.checked)}
              className="w-4 h-4 accent-orange-500 cursor-pointer" />
            <label htmlFor="freq" className="text-sm text-gray-700 cursor-pointer">
              Habilitar controle de frequência
            </label>
          </div>

          {erro && (
            <p className="col-span-2 text-sm text-red-500 bg-red-50 border border-red-100 rounded-lg px-3 py-2">{erro}</p>
          )}

          <div className="col-span-2 flex gap-3 pt-2">
            <button type="submit" disabled={loading}
              className="bg-orange-500 hover:bg-orange-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium transition disabled:opacity-60">
              {loading ? 'Cadastrando...' : 'Cadastrar aluno'}
            </button>
            <Link href="/admin/alunos"
              className="px-6 py-2.5 rounded-lg text-sm font-medium border border-gray-200 text-gray-600 hover:bg-gray-50 transition">
              Cancelar
            </Link>
          </div>
        </form>
      </div>
    </div>
  )
}
