'use client'
import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { supabase } from '../../lib/supabase'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'

const NAV = [
  { href: '/admin', label: 'Dashboard', emoji: '📊', exact: true },
  { href: '/admin/alunos', label: 'Alunos', emoji: '👥' },
  { href: '/admin/mensalidades', label: 'Mensalidades', emoji: '💳' },
  { href: '/admin/instrutores', label: 'Instrutores', emoji: '🏋️' },
  { href: '/admin/planos', label: 'Planos', emoji: '📋' },
  { href: '/admin/relatorios', label: 'Relatórios', emoji: '📄' },
]

const TIPO_LABEL = { admin: 'Admin', recepcionista: 'Recepcionista', instrutor: 'Instrutor' }

export default function AdminLayout({ children }) {
  const router = useRouter()
  const pathname = usePathname()
  const [perfil, setPerfil] = useState(null)

  useEffect(() => {
    async function checkAuth() {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) { router.replace('/login'); return }
      try {
        const res = await fetch(`${API_URL}/auth/me`, {
          headers: { Authorization: `Bearer ${session.access_token}` },
        })
        const profile = await res.json()
        if (profile.tipo === 'aluno') { router.replace('/'); return }
        setPerfil(profile)
      } catch {
        router.replace('/login')
      }
    }
    checkAuth()
  }, [router])

  async function logout() {
    await supabase.auth.signOut()
    router.replace('/login')
  }

  return (
    <div className="flex min-h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-gray-100 flex flex-col fixed top-0 left-0 h-full z-10">
        {/* Logo */}
        <div className="p-4 border-b border-gray-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 bg-orange-500 rounded-lg flex items-center justify-center text-white font-bold text-sm flex-shrink-0">G</div>
            <div className="min-w-0">
              <p className="font-bold text-gray-800 text-sm leading-tight truncate">GestãoAcademia</p>
              <p className="text-xs text-gray-400">Sistema de gestão</p>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-2 space-y-0.5 overflow-y-auto">
          {NAV.map(({ href, label, emoji, exact }) => {
            const active = exact ? pathname === href : pathname.startsWith(href)
            return (
              <Link key={href} href={href}
                className={`flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition
                  ${active ? 'bg-orange-50 text-orange-600' : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'}`}>
                <span className="text-base">{emoji}</span>
                {label}
              </Link>
            )
          })}
        </nav>

        {/* Usuário */}
        <div className="p-3 border-t border-gray-100">
          {perfil && (
            <div className="mb-2 px-2">
              <p className="text-xs font-semibold text-gray-800 truncate">{perfil.nome}</p>
              <p className="text-xs text-orange-500">{TIPO_LABEL[perfil.tipo] || perfil.tipo}</p>
            </div>
          )}
          <button onClick={logout}
            className="flex items-center gap-2 px-2 py-1.5 text-xs text-gray-500 hover:text-red-500 transition rounded-lg hover:bg-red-50 w-full">
            <span>🚪</span> Sair
          </button>
        </div>
      </aside>

      {/* Conteúdo principal */}
      <div className="flex-1 ml-56 flex flex-col min-h-screen">
        {/* Topbar */}
        <header className="bg-white border-b border-gray-100 px-6 py-3 flex items-center justify-between sticky top-0 z-[5]">
          <p className="text-sm text-gray-600">
            Olá, <strong className="text-gray-900">{perfil?.nome ?? '...'}</strong>!
          </p>
          {perfil && (
            <span className="text-xs bg-orange-100 text-orange-700 px-2.5 py-0.5 rounded-full font-medium">
              {TIPO_LABEL[perfil.tipo] || perfil.tipo}
            </span>
          )}
        </header>

        <main className="flex-1 p-6">
          {children}
        </main>
      </div>
    </div>
  )
}
