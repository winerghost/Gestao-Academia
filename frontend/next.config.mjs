/** @type {import('next').NextConfig} */

// Cabeçalhos de segurança aplicados a todas as rotas servidas pelo Next.
// Estes são "seguros" — não quebram a hidratação do React:
//   - X-Frame-Options: DENY        → impede clickjacking (app em <iframe>).
//   - X-Content-Type-Options       → impede MIME sniffing.
//   - Referrer-Policy              → não vaza a URL completa para terceiros.
//   - Strict-Transport-Security    → força HTTPS (ignorado em http/localhost).
// OBS.: a Content-Security-Policy (mitigação central de XSS / roubo de token)
// NÃO está aqui de propósito: uma CSP estrita no App Router precisa de nonce
// via middleware, senão quebra os scripts inline de hidratação. Fica como
// tarefa dedicada (a ser testada no navegador).
const securityHeaders = [
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  {
    key: 'Strict-Transport-Security',
    value: 'max-age=63072000; includeSubDomains; preload',
  },
]

const nextConfig = {
  async headers() {
    return [
      {
        source: '/:path*',
        headers: securityHeaders,
      },
    ]
  },
}

export default nextConfig;
