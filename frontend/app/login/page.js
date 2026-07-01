'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '../../lib/supabase'
import { login as apiLogin, getMe } from '../../lib/api'
import FormField, { inputClass } from '@/components/FormField'
import Toast from '@/components/Toast'
import { useToast } from '@/hooks/useToast'

export default function Login() {
  const router = useRouter()
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [fieldErrors, setFieldErrors] = useState({})
  const [erro, setErro] = useState('')
  const [loading, setLoading] = useState(false)
  const { toast, show } = useToast()

  async function handleLogin(e) {
    e.preventDefault()
    setErro('')
    setFieldErrors({})
    setLoading(true)

    try {
      // 1. Credenciais validadas no Flask (/auth/login) — não diretamente no Supabase.
      //    Isso garante: client anon isolado por requisição, rate-limit no backend,
      //    e permite futuramente adicionar lógica extra (ex.: bloqueio de IP).
      const { access_token, refresh_token } = await apiLogin(email, senha)

      // 2. Hidrata o SDK do Supabase com os tokens retornados pelo backend.
      //    A partir daqui, qualquer page pode chamar supabase.auth.getSession()
      //    para obter o token sem fazer nova requisição à rede.
      await supabase.auth.setSession({ access_token, refresh_token })

      const profile = await getMe(access_token)
      show('Bem-vindo!', 'success')
      router.replace(profile.tipo === 'aluno' ? '/' : '/admin')
    } catch (err) {
      setFieldErrors(err.fields || {})
      setErro(Object.keys(err.fields || {}).length ? '' : err.message)
      setLoading(false)
      const first = Object.keys(err.fields || {})[0]
      if (first) document.getElementById(first)?.focus()
    }
  }

  return (
    <div className="min-h-screen flex">
      {/* Painel esquerdo */}
      <div className="hidden lg:flex w-1/2 bg-gray-900 flex-col justify-between p-12">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-orange-500 rounded-xl flex items-center justify-center text-white font-bold text-lg">G</div>
          <span className="text-white font-bold text-lg">GestãoAcademia</span>
        </div>
        <div>
          <h1 className="text-4xl font-bold text-white leading-tight mb-6">
            Gerencie sua academia em um só lugar.
          </h1>
          <ul className="space-y-3">
            {[
              'Controle de alunos e mensalidades',
              'Relatórios financeiros detalhados',
              'Portal do aluno integrado',
            ].map(item => (
              <li key={item} className="flex items-center gap-3 text-gray-300 text-sm">
                <span className="text-orange-500 font-bold">✓</span> {item}
              </li>
            ))}
          </ul>
        </div>
        <p className="text-gray-600 text-xs">© 2026 GestãoAcademia</p>
      </div>

      {/* Painel direito */}
      <div className="flex-1 flex items-center justify-center px-6 bg-stone-50">
        <div className="w-full max-w-sm">
          {/* Logo mobile */}
          <div className="flex items-center gap-2 mb-8 lg:hidden">
            <div className="w-8 h-8 bg-orange-500 rounded-lg flex items-center justify-center text-white font-bold">G</div>
            <span className="font-bold text-gray-800">GestãoAcademia</span>
          </div>

          <div className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900">Entrar na sua conta</h2>
            <p className="text-sm text-gray-500 mt-1">Digite suas credenciais para continuar</p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <FormField label="E-mail" required error={fieldErrors.email}>
              <input
                id="email"
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                placeholder="seu@email.com"
                className={inputClass(!!fieldErrors.email)}
              />
            </FormField>

            <FormField label="Senha" required error={fieldErrors.password || fieldErrors.senha}>
              <input
                id="password"
                type="password"
                value={senha}
                onChange={e => setSenha(e.target.value)}
                required
                placeholder="••••••••"
                className={inputClass(!!fieldErrors.password || !!fieldErrors.senha)}
              />
            </FormField>

            {erro && (
              <p className="text-sm text-red-500 bg-red-50 border border-red-100 rounded-lg px-3 py-2">{erro}</p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-gray-900 hover:bg-gray-800 text-white font-medium py-2.5 rounded-lg text-sm transition disabled:opacity-60"
            >
              {loading ? 'Entrando...' : 'Entrar'}
            </button>
          </form>
        </div>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} />}
    </div>
  )
}
