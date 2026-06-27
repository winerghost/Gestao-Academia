// Aplicação das preferências de aparência (cor de destaque + tamanho de fonte).
//
// A cor é exposta como a CSS var `--cor-destaque` no <html>, consumida pelas
// telas de Configurações. O tamanho de fonte ajusta o `font-size` da raiz —
// como o Tailwind usa `rem`, isso escala toda a interface.

export const COR_PADRAO = '#f97316' // laranja (orange-500), tom atual do sistema

export const CORES_DESTAQUE = [
  { nome: 'Laranja', valor: '#f97316' },
  { nome: 'Azul',    valor: '#3c8dbc' },
  { nome: 'Verde',   valor: '#16a34a' },
  { nome: 'Roxo',    valor: '#7c3aed' },
  { nome: 'Vermelho',valor: '#dc2626' },
  { nome: 'Rosa',    valor: '#db2777' },
]

export const TAMANHOS_FONTE = {
  pequena: '14px',
  normal:  '16px',
  grande:  '18px',
}

const STORAGE_KEY = 'ga_tema'

export function lerTemaLocal() {
  if (typeof window === 'undefined') return {}
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}
  } catch {
    return {}
  }
}

export function aplicarTema(prefs = {}) {
  if (typeof document === 'undefined') return
  const cor = prefs.cor_destaque || COR_PADRAO
  const fonte = TAMANHOS_FONTE[prefs.tamanho_fonte] || TAMANHOS_FONTE.normal

  const root = document.documentElement
  root.style.setProperty('--cor-destaque', cor)
  root.style.fontSize = fonte

  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      cor_destaque: cor,
      tamanho_fonte: prefs.tamanho_fonte || 'normal',
    }))
  } catch { /* localStorage indisponível — segue só com o estilo aplicado */ }
}
