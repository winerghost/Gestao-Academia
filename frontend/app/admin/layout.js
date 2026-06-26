'use client'
import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { supabase } from '../../lib/supabase'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'

const NAV = [
  { href: '/admin',               label: 'Dashboard',    icon: '⊞',  exact: true },
  { href: '/admin/alunos',        label: 'Alunos',       icon: '👥' },
  { href: '/admin/mensalidades',  label: 'Mensalidades', icon: '💳' },
  { href: '/admin/avaliacoes',    label: 'Avaliações',   icon: '📊' },
  { href: '/admin/instrutores',   label: 'Instrutores',  icon: '🏋️' },
  { href: '/admin/planos',        label: 'Planos',       icon: '📋' },
  { href: '/admin/relatorios',    label: 'Relatórios',   icon: '📄' },
]

const TIPO_LABEL = { admin: 'Administrador', recepcionista: 'Recepcionista', instrutor: 'Instrutor' }

function initials(nome = '') {
  return nome.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase() || 'GA'
}

export default function AdminLayout({ children }) {
  const router   = useRouter()
  const pathname = usePathname()
  const [perfil,       setPerfil]       = useState(null)
  const [sidebarOpen,  setSidebarOpen]  = useState(true)
  const [userMenuOpen, setUserMenuOpen] = useState(false)

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

  const pageLabel = NAV.find(n => n.exact ? pathname === n.href : pathname.startsWith(n.href))?.label ?? 'Painel'

  return (
    <div className="min-h-screen" style={{ backgroundColor: '#ecf0f5' }}>

      {/* ── Navbar superior ─────────────────────────────── */}
      <nav
        className="fixed top-0 left-0 right-0 z-30 flex items-center h-12"
        style={{ backgroundColor: '#3c8dbc' }}
      >
        {/* Hamburguer + brand */}
        <div
          className="flex items-center h-full px-4 flex-shrink-0 transition-all duration-200"
          style={{ width: sidebarOpen ? 224 : 64, backgroundColor: '#367fa9' }}
        >
          <button
            onClick={() => setSidebarOpen(o => !o)}
            className="text-white opacity-80 hover:opacity-100 transition text-xl mr-3 leading-none"
            aria-label="toggle sidebar"
          >
            ☰
          </button>
          {sidebarOpen && (
            <span className="text-white font-semibold text-sm tracking-wide whitespace-nowrap">
              GestãoAcademia
            </span>
          )}
        </div>

        {/* Título da página atual */}
        <span className="text-white text-sm font-medium px-4 opacity-90 hidden md:block">
          {pageLabel}
        </span>

        {/* Espaço */}
        <div className="flex-1" />

        {/* Menu do usuário */}
        <div className="relative px-3">
          <button
            onClick={() => setUserMenuOpen(o => !o)}
            className="flex items-center gap-2 text-white opacity-90 hover:opacity-100 transition py-2"
          >
            <div
              className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0"
              style={{ backgroundColor: '#2a6496' }}
            >
              {initials(perfil?.nome)}
            </div>
            <span className="text-sm hidden md:block">{perfil?.nome ?? '...'}</span>
            <span className="text-xs opacity-70">▾</span>
          </button>

          {userMenuOpen && (
            <div
              className="absolute right-0 top-full mt-0.5 w-44 rounded shadow-lg py-1 z-40"
              style={{ backgroundColor: '#fff' }}
            >
              <div className="px-4 py-2 border-b border-gray-100">
                <p className="text-xs font-semibold text-gray-800 truncate">{perfil?.nome}</p>
                <p className="text-xs text-gray-400">{TIPO_LABEL[perfil?.tipo] || perfil?.tipo}</p>
              </div>
              <button
                onClick={logout}
                className="flex items-center gap-2 w-full px-4 py-2 text-sm text-red-500 hover:bg-red-50 transition"
              >
                <span>🚪</span> Sair
              </button>
            </div>
          )}
        </div>
      </nav>

      {/* Overlay para fechar dropdown */}
      {userMenuOpen && (
        <div className="fixed inset-0 z-20" onClick={() => setUserMenuOpen(false)} />
      )}

      {/* ── Sidebar ─────────────────────────────────────── */}
      <aside
        className="fixed top-12 left-0 bottom-0 z-20 flex flex-col overflow-hidden transition-all duration-200"
        style={{ width: sidebarOpen ? 224 : 64, backgroundColor: '#222d32' }}
      >
        {/* User panel */}
        {sidebarOpen && (
          <div
            className="flex items-center gap-3 px-4 py-4"
            style={{ backgroundColor: '#1a2226' }}
          >
            <div
              className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold text-white flex-shrink-0"
              style={{ backgroundColor: '#3c8dbc' }}
            >
              {initials(perfil?.nome)}
            </div>
            <div className="min-w-0">
              <p className="text-white text-sm font-semibold truncate leading-tight">
                {perfil?.nome ?? '...'}
              </p>
              <span className="flex items-center gap-1 mt-0.5">
                <span className="w-2 h-2 rounded-full bg-green-400 inline-block" />
                <span className="text-xs" style={{ color: '#8aa4af' }}>
                  {TIPO_LABEL[perfil?.tipo] || '...'}
                </span>
              </span>
            </div>
          </div>
        )}

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-2">
          {/* Seção */}
          {sidebarOpen && (
            <div
              className="px-4 py-1.5 text-[10px] font-semibold uppercase tracking-widest"
              style={{ color: '#4b6269' }}
            >
              Menu principal
            </div>
          )}

          {NAV.map(({ href, label, icon, exact }) => {
            const active = exact ? pathname === href : pathname.startsWith(href)
            return (
              <Link
                key={href}
                href={href}
                title={!sidebarOpen ? label : undefined}
                className="flex items-center h-10 transition-colors duration-150"
                style={{
                  backgroundColor: active ? '#1e282c' : 'transparent',
                  borderLeft: active ? '3px solid #3c8dbc' : '3px solid transparent',
                  color: active ? '#fff' : '#8aa4af',
                  paddingLeft: sidebarOpen ? (active ? 13 : 16) : 0,
                  justifyContent: sidebarOpen ? 'flex-start' : 'center',
                }}
                onMouseEnter={e => { if (!active) e.currentTarget.style.backgroundColor = '#1e282c' }}
                onMouseLeave={e => { if (!active) e.currentTarget.style.backgroundColor = 'transparent' }}
              >
                <span className="text-base leading-none" style={{ minWidth: 20, textAlign: 'center' }}>
                  {icon}
                </span>
                {sidebarOpen && (
                  <span className="ml-3 text-sm font-medium">{label}</span>
                )}
              </Link>
            )
          })}
        </nav>

        {/* Rodapé sidebar */}
        {sidebarOpen && (
          <div className="px-4 py-3 text-center" style={{ borderTop: '1px solid #1a2226' }}>
            <span className="text-[10px]" style={{ color: '#4b6269' }}>
              GestãoAcademia v1.0
            </span>
          </div>
        )}
      </aside>

      {/* ── Conteúdo ────────────────────────────────────── */}
      <div
        className="transition-all duration-200 flex flex-col min-h-screen pt-12"
        style={{ marginLeft: sidebarOpen ? 224 : 64 }}
      >
        {/* Content header (breadcrumb) */}
        <div className="px-6 py-3 flex items-center gap-2" style={{ backgroundColor: '#ecf0f5' }}>
          <h1 className="text-xl font-semibold text-gray-700">{pageLabel}</h1>
          <span className="text-gray-400 text-sm">/ {pageLabel}</span>
        </div>
        <hr style={{ borderColor: '#d2d6de', marginBottom: 0 }} />

        {/* Content wrapper */}
        <main className="flex-1 p-6">
          {children}
        </main>

        {/* Footer */}
        <footer
          className="px-6 py-3 text-xs border-t"
          style={{ backgroundColor: '#fff', borderColor: '#d2d6de', color: '#666' }}
        >
          <strong>GestãoAcademia</strong> &copy; {new Date().getFullYear()}
          <span className="float-right">Versão 1.0</span>
        </footer>
      </div>
    </div>
  )
}
