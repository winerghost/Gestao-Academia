'use client'
import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { supabase } from '../../lib/supabase'
import { getMe, logout as apiLogout } from '../../lib/api'
import { aplicarTema, lerTemaLocal } from '../../lib/tema'

const NAV = [
  { href: '/admin',               label: 'Dashboard',     icon: '⊞',  exact: true },
  { href: '/admin/alunos',        label: 'Alunos',        icon: '👥' },
  { href: '/admin/mensalidades',  label: 'Mensalidades',  icon: '💳' },
  { href: '/admin/avaliacoes',    label: 'Avaliações',    icon: '📊' },
  { href: '/admin/instrutores',   label: 'Instrutores',   icon: '🏋️' },
  { href: '/admin/planos',        label: 'Planos',        icon: '📋' },
  { href: '/admin/relatorios',    label: 'Relatórios',    icon: '📄' },
  { href: '/admin/configuracoes', label: 'Configurações', icon: '⚙️' },
]

const TIPO_LABEL = { admin: 'Administrador', recepcionista: 'Recepcionista', instrutor: 'Instrutor' }

function initials(nome = '') {
  return nome.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase() || 'GA'
}

// Foto do usuário com fallback para iniciais (se não houver foto ou a URL falhar).
function Avatar({ url, nome, size, fontClass, bg }) {
  const [erro, setErro] = useState(false)
  // Reseta o erro quando a URL muda (ajuste de estado durante o render).
  const [urlAnterior, setUrlAnterior] = useState(url)
  if (url !== urlAnterior) {
    setUrlAnterior(url)
    setErro(false)
  }
  if (url && !erro) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- avatar pequeno, URL remota (Supabase/Gravatar); next/image exigiria remotePatterns sem ganho real
      <img
        src={url}
        alt=""
        onError={() => setErro(true)}
        className={`${size} rounded-full object-cover flex-shrink-0`}
      />
    )
  }
  return (
    <div
      className={`${size} ${fontClass} rounded-full flex items-center justify-center flex-shrink-0 text-white`}
      style={{ backgroundColor: bg }}
    >
      {initials(nome)}
    </div>
  )
}

export default function AdminLayout({ children }) {
  const router   = useRouter()
  const pathname = usePathname()
  const [perfil,       setPerfil]       = useState(null)
  const [sidebarOpen,  setSidebarOpen]  = useState(true)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [isMobile,     setIsMobile]     = useState(false)

  useEffect(() => {
    function checkMobile() {
      const mobile = window.innerWidth < 768
      setIsMobile(mobile)
      if (mobile) setSidebarOpen(false)
    }
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  // Aplica o tema em cache no primeiro paint (evita "flash" de cor padrão).
  useEffect(() => { aplicarTema(lerTemaLocal()) }, [])

  // A tela de Conta emite este evento ao trocar/remover a foto — reflete
  // na navbar e na sidebar sem precisar recarregar a página.
  useEffect(() => {
    function onAvatar(e) {
      setPerfil(p => (p ? { ...p, avatar_url: e.detail } : p))
    }
    window.addEventListener('avatar-atualizado', onAvatar)
    return () => window.removeEventListener('avatar-atualizado', onAvatar)
  }, [])

  useEffect(() => {
    async function checkAuth() {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) { router.replace('/login'); return }
      try {
        const profile = await getMe(session.access_token)
        if (profile.tipo === 'aluno') { router.replace('/'); return }
        setPerfil(profile)
        // Reaplica com as preferências salvas no servidor (fonte da verdade).
        if (profile.preferencias) aplicarTema(profile.preferencias)
        // Honra preferência de sidebar compacta.
        if (profile.preferencias?.sidebar_compacta && window.innerWidth >= 768) {
          setSidebarOpen(false)
        }
      } catch {
        router.replace('/login')
      }
    }
    checkAuth()
  }, [router])

  async function logout() {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      if (session) await apiLogout(session.access_token)
    } catch { /* segue para o signOut local mesmo se a revogação falhar */ }
    await supabase.auth.signOut()
    router.replace('/login')
  }

  const pageLabel = NAV.find(n => n.exact ? pathname === n.href : pathname.startsWith(n.href))?.label ?? 'Painel'

  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--bg-content)' }}>

      {/* ── Navbar superior ─────────────────────────────── */}
      <nav
        className="fixed top-0 left-0 right-0 z-30 flex items-center h-12"
        style={{ backgroundColor: 'var(--cor-destaque)' }}
      >
        {/* Hamburguer + brand */}
        <div
          className="flex items-center h-full px-4 flex-shrink-0 transition-all duration-200"
          style={{ width: sidebarOpen ? 224 : 64, backgroundColor: 'var(--bg-navbar-brand)' }}
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
            <Avatar
              url={perfil?.avatar_url}
              nome={perfil?.nome}
              size="w-7 h-7"
              fontClass="text-xs font-bold"
              bg="rgba(0,0,0,0.25)"
            />
            <span className="text-sm hidden md:block">{perfil?.nome ?? '...'}</span>
            <span className="text-xs opacity-70">▾</span>
          </button>

          {userMenuOpen && (
            <div
              className="absolute right-0 top-full mt-0.5 w-44 rounded shadow-lg py-1 z-40"
              style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}
            >
              <div className="px-4 py-2" style={{ borderBottom: '1px solid var(--border-color)' }}>
                <p className="text-xs font-semibold truncate" style={{ color: 'var(--text-primary)' }}>
                  {perfil?.nome}
                </p>
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  {TIPO_LABEL[perfil?.tipo] || perfil?.tipo}
                </p>
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

      {/* Overlay mobile para fechar sidebar */}
      {isMobile && sidebarOpen && (
        <div className="fixed inset-0 z-30 bg-black/50" onClick={() => setSidebarOpen(false)} />
      )}

      {/* ── Sidebar ─────────────────────────────────────── */}
      <aside
        className="fixed top-12 left-0 bottom-0 flex flex-col overflow-hidden transition-all duration-200"
        style={{
          width: isMobile ? 224 : (sidebarOpen ? 224 : 64),
          backgroundColor: 'var(--bg-sidebar)',
          transform: isMobile && !sidebarOpen ? 'translateX(-100%)' : 'translateX(0)',
          zIndex: isMobile ? 40 : 20,
        }}
      >
        {/* User panel */}
        {(sidebarOpen || isMobile) && (
          <div
            className="flex items-center gap-3 px-4 py-4"
            style={{ backgroundColor: 'var(--bg-sidebar-header)' }}
          >
            <Avatar
              url={perfil?.avatar_url}
              nome={perfil?.nome}
              size="w-9 h-9"
              fontClass="text-sm font-bold"
              bg="var(--cor-destaque)"
            />
            <div className="min-w-0">
              <p className="text-sm font-semibold truncate leading-tight" style={{ color: 'var(--text-sidebar-name)' }}>
                {perfil?.nome ?? '...'}
              </p>
              <span className="flex items-center gap-1 mt-0.5">
                <span className="w-2 h-2 rounded-full bg-green-400 inline-block" />
                <span className="text-xs" style={{ color: 'var(--nav-text)' }}>
                  {TIPO_LABEL[perfil?.tipo] || '...'}
                </span>
              </span>
            </div>
          </div>
        )}

        {/* Nav */}
        <nav className="flex-1 overflow-y-auto py-2">
          {(sidebarOpen || isMobile) && (
            <div
              className="px-4 py-1.5 text-[10px] font-semibold uppercase tracking-widest"
              style={{ color: 'var(--nav-label)' }}
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
                title={!sidebarOpen && !isMobile ? label : undefined}
                className="flex items-center h-10 transition-colors duration-150"
                style={{
                  backgroundColor: active ? 'var(--nav-active)' : 'transparent',
                  borderLeft: active ? '3px solid var(--cor-destaque)' : '3px solid transparent',
                  color: active ? '#fff' : 'var(--nav-text)',
                  paddingLeft: (sidebarOpen || isMobile) ? (active ? 13 : 16) : 0,
                  justifyContent: (sidebarOpen || isMobile) ? 'flex-start' : 'center',
                }}
                onMouseEnter={e => { if (!active) e.currentTarget.style.backgroundColor = 'var(--nav-active)' }}
                onMouseLeave={e => { if (!active) e.currentTarget.style.backgroundColor = 'transparent' }}
              >
                <span className="text-base leading-none" style={{ minWidth: 20, textAlign: 'center' }}>
                  {icon}
                </span>
                {(sidebarOpen || isMobile) && (
                  <span className="ml-3 text-sm font-medium">{label}</span>
                )}
              </Link>
            )
          })}
        </nav>

        {/* Rodapé sidebar */}
        {(sidebarOpen || isMobile) && (
          <div className="px-4 py-3 text-center" style={{ borderTop: '1px solid var(--bg-sidebar-header)' }}>
            <span className="text-[10px]" style={{ color: 'var(--nav-label)' }}>
              GestãoAcademia v1.0
            </span>
          </div>
        )}
      </aside>

      {/* ── Conteúdo ────────────────────────────────────── */}
      <div
        className="transition-all duration-200 flex flex-col min-h-screen pt-12"
        style={{ marginLeft: isMobile ? 0 : (sidebarOpen ? 224 : 64) }}
      >
        {/* Content header */}
        <div className="px-6 py-3 flex items-center gap-2" style={{ backgroundColor: 'var(--bg-content)' }}>
          <h1 className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>{pageLabel}</h1>
          <span className="text-sm" style={{ color: 'var(--text-muted)' }}>/ {pageLabel}</span>
        </div>
        <hr style={{ borderColor: 'var(--hr-color)', marginBottom: 0 }} />

        {/* Content wrapper */}
        <main className="flex-1 p-6">
          {children}
        </main>

        {/* Footer */}
        <footer
          className="px-6 py-3 text-xs border-t"
          style={{ backgroundColor: 'var(--footer-bg)', borderColor: 'var(--border-color)', color: 'var(--footer-text)' }}
        >
          <strong>GestãoAcademia</strong> &copy; {new Date().getFullYear()}
          <span className="float-right">Versão 1.0</span>
        </footer>
      </div>
    </div>
  )
}
