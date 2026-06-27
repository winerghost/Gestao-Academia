export const COR_PADRAO = '#f97316'

export const CORES_DESTAQUE = [
  { nome: 'Laranja',  valor: '#f97316' },
  { nome: 'Azul',     valor: '#3c8dbc' },
  { nome: 'Verde',    valor: '#16a34a' },
  { nome: 'Roxo',     valor: '#7c3aed' },
  { nome: 'Vermelho', valor: '#dc2626' },
  { nome: 'Rosa',     valor: '#db2777' },
  { nome: 'Ciano',    valor: '#0891b2' },
  { nome: 'Âmbar',   valor: '#d97706' },
]

export const TAMANHOS_FONTE = {
  pequena: '14px',
  normal:  '16px',
  grande:  '18px',
}

export const MODOS = [
  { valor: 'claro',   label: 'Claro',   icone: '☀️' },
  { valor: 'escuro',  label: 'Escuro',  icone: '🌙' },
  { valor: 'sistema', label: 'Sistema', icone: '💻' },
]

const STORAGE_KEY = 'ga_tema'

export function lerTemaLocal() {
  if (typeof window === 'undefined') return {}
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}
  } catch {
    return {}
  }
}

function resolverModo(modo) {
  if (modo === 'escuro') return true
  if (modo === 'sistema') return window.matchMedia('(prefers-color-scheme: dark)').matches
  return false
}

export function aplicarTema(prefs = {}) {
  if (typeof document === 'undefined') return
  const root = document.documentElement

  const cor    = prefs.cor_destaque  || COR_PADRAO
  const fonte  = TAMANHOS_FONTE[prefs.tamanho_fonte] || TAMANHOS_FONTE.normal
  const modo   = prefs.modo || 'claro'
  const isDark = resolverModo(modo)

  root.style.setProperty('--cor-destaque', cor)
  root.style.fontSize = fonte

  if (isDark) {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      cor_destaque:  cor,
      tamanho_fonte: prefs.tamanho_fonte || 'normal',
      modo,
    }))
  } catch { /* localStorage indisponível */ }
}
