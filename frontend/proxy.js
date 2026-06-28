import { NextResponse } from 'next/server'

// ── Content-Security-Policy (mitigação central de XSS / roubo de token) ─────────
//
// Next 16: este arquivo é o "proxy" (antigo middleware). Ele gera um nonce por
// requisição e marca os scripts do próprio Next com ele — assim a CSP pode ser
// estrita (sem 'unsafe-inline' em script) sem quebrar a hidratação.
//
// MODO SEGURO POR PADRÃO (REPORT_ONLY = true):
//   - O navegador NÃO bloqueia nada; apenas reporta violações no console.
//   - Use para validar: abra cada tela (login, dashboard, foto via webcam,
//     avatares, gráficos) e veja se aparece "[Report Only] Refused to..." no
//     console. Cada violação indica uma origem que falta liberar abaixo.
//   - Quando o console estiver limpo, troque REPORT_ONLY para false para
//     PASSAR A BLOQUEAR de verdade.
const REPORT_ONLY = true

export function proxy(request) {
  const nonce = Buffer.from(crypto.randomUUID()).toString('base64')
  const isDev = process.env.NODE_ENV === 'development'

  // Origens externas legítimas deste app (derivadas do .env):
  //  - API Flask (fetch de dados)          → connect-src
  //  - Supabase (auth via supabase-js)     → connect-src
  //  - Supabase Storage + Gravatar (fotos) → img-src
  const api = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'
  const supabase = process.env.NEXT_PUBLIC_SUPABASE_URL || ''
  const connectSrc = ["'self'", api, supabase].filter(Boolean).join(' ')
  const imgSrc = ["'self'", 'data:', 'blob:', supabase, 'https://gravatar.com'].filter(Boolean).join(' ')

  // 'unsafe-eval' só em dev (React usa eval p/ debug; produção não precisa).
  // style-src usa 'unsafe-inline' porque o app usa estilos inline (style={{...}});
  // estilos não são vetor relevante de XSS de execução.
  const csp = `
    default-src 'self';
    script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${isDev ? " 'unsafe-eval'" : ''};
    style-src 'self' 'unsafe-inline';
    img-src ${imgSrc};
    font-src 'self' data:;
    connect-src ${connectSrc};
    object-src 'none';
    base-uri 'self';
    form-action 'self';
    frame-ancestors 'none';
    ${isDev ? '' : 'upgrade-insecure-requests;'}
  `.replace(/\s{2,}/g, ' ').trim()

  const requestHeaders = new Headers(request.headers)
  requestHeaders.set('x-nonce', nonce)
  // Sinaliza ao Next para aplicar o nonce nos próprios scripts (mesmo em
  // report-only), garantindo que o "flip" para bloqueio seja transparente.
  requestHeaders.set('Content-Security-Policy', csp)

  const response = NextResponse.next({ request: { headers: requestHeaders } })
  response.headers.set(
    REPORT_ONLY ? 'Content-Security-Policy-Report-Only' : 'Content-Security-Policy',
    csp,
  )
  return response
}

export const config = {
  // Não aplica em rotas de API, assets estáticos, otimização de imagem e
  // favicon; ignora prefetches do next/link (não precisam da CSP).
  matcher: [
    {
      source: '/((?!api|_next/static|_next/image|favicon.ico).*)',
      missing: [
        { type: 'header', key: 'next-router-prefetch' },
        { type: 'header', key: 'purpose', value: 'prefetch' },
      ],
    },
  ],
}
