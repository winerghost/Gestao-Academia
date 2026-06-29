/** @type {import('next').NextConfig} */

// Cabeçalhos de segurança aplicados a todas as rotas pelo Next (incluindo
// assets estáticos que o proxy.js não intercepta).
// A Content-Security-Policy com nonce é gerada por request em proxy.js —
// mais segura que um valor estático, porque impede scripts inline externos.
// Estes headers complementam o CSP para assets estáticos:
//   - X-Frame-Options: DENY        → impede clickjacking (redundante com
//                                    frame-ancestors do CSP, mas defense-in-depth).
//   - X-Content-Type-Options       → impede MIME sniffing.
//   - Referrer-Policy              → não vaza URL completa para terceiros.
//   - Strict-Transport-Security    → força HTTPS (ignorado em http/localhost).
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
  // standalone: gera um bundle auto-suficiente em .next/standalone/
  // com um server.js mínimo — ideal para Docker (imagem ~3× menor).
  output: 'standalone',

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
