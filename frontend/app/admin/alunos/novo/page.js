'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '../../../../hooks/useAuth'
import { criarAluno } from '../../../../lib/api'
import { mascaraTelefone } from '../../../../lib/masks'
import CapturaFoto from '@/components/CapturaFoto'
import FormField, { inputClass } from '@/components/FormField'
import Toast from '@/components/Toast'
import { useToast } from '@/hooks/useToast'

export default function NovoAluno() {
  const router = useRouter()
  const { token } = useAuth()
  const [form, setForm] = useState({
    nome: '', email: '', senha: '', cpf: '', telefone: '',
    data_nascimento: '', endereco: '', status: 'ativo',
    frequencia_habilitada: false, foto: null,
  })
  const [fieldErrors, setFieldErrors] = useState({})
  const [erro, setErro] = useState('')
  const [loading, setLoading] = useState(false)
  const { toast, show } = useToast()

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  async function handleSubmit(e) {
    e.preventDefault()
    setErro('')
    setFieldErrors({})
    setLoading(true)
    try {
      await criarAluno(token, form)
      show('Aluno cadastrado com sucesso!', 'success')
      router.push('/admin/alunos')
    } catch (err) {
      setFieldErrors(err.fields || {})
      setErro(Object.keys(err.fields || {}).length ? '' : err.message)
      setLoading(false)
      const first = Object.keys(err.fields || {})[0]
      if (first) document.getElementById(first)?.focus()
    }
  }

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
          <FormField label="Foto do aluno" className="col-span-2">
            <CapturaFoto value={form.foto} nome={form.nome} onChange={d => set('foto', d)} disabled={loading} />
            <p className="text-xs text-gray-400 mt-2">
              Se o e-mail do aluno tiver um Gravatar, ele será usado no lugar desta foto.
            </p>
          </FormField>

          <FormField label="Nome completo" required error={fieldErrors.nome} className="col-span-2">
            <input id="nome" className={inputClass(!!fieldErrors.nome)} value={form.nome} onChange={e => set('nome', e.target.value)} required placeholder="João da Silva" />
          </FormField>

          <FormField label="E-mail" required error={fieldErrors.email}>
            <input id="email" type="email" className={inputClass(!!fieldErrors.email)} value={form.email} onChange={e => set('email', e.target.value)} required placeholder="joao@email.com" />
          </FormField>

          <FormField label="Senha" required error={fieldErrors.senha}>
            <input id="senha" type="password" className={inputClass(!!fieldErrors.senha)} value={form.senha} onChange={e => set('senha', e.target.value)} required placeholder="Mínimo 8 caracteres" />
          </FormField>

          <FormField label="CPF" required error={fieldErrors.cpf}>
            <input id="cpf" className={inputClass(!!fieldErrors.cpf)} value={form.cpf} onChange={e => set('cpf', e.target.value)} required placeholder="000.000.000-00" />
          </FormField>

          <FormField label="Telefone" error={fieldErrors.telefone}>
            <input id="telefone" className={inputClass(!!fieldErrors.telefone)} value={form.telefone} onChange={e => set('telefone', mascaraTelefone(e.target.value))} placeholder="(11) 99999-9999" maxLength="15" />
          </FormField>

          <FormField label="Data de nascimento" error={fieldErrors.data_nascimento}>
            <input id="data_nascimento" type="date" className={inputClass(!!fieldErrors.data_nascimento)} value={form.data_nascimento} onChange={e => set('data_nascimento', e.target.value)} />
          </FormField>

          <FormField label="Endereço" error={fieldErrors.endereco} className="col-span-2">
            <input id="endereco" className={inputClass(!!fieldErrors.endereco)} value={form.endereco} onChange={e => set('endereco', e.target.value)} placeholder="Rua, número, bairro, cidade" />
          </FormField>

          <FormField label="Status" error={fieldErrors.status}>
            <select id="status" className={inputClass(!!fieldErrors.status)} value={form.status} onChange={e => set('status', e.target.value)}>
              <option value="ativo">Ativo</option>
              <option value="inativo">Inativo</option>
            </select>
          </FormField>

          <div className="flex items-center gap-3 pt-4">
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

      {toast && <Toast message={toast.message} type={toast.type} />}
    </div>
  )
}
