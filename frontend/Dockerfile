# ── Stage 1: build ────────────────────────────────────────────────────────────
# Compila o Next.js com todas as devDependencies (TypeScript, tailwind, etc.).
# ARGs: variáveis públicas do Next.js (NEXT_PUBLIC_*) são embutidas no bundle
# em build time — precisam estar disponíveis aqui, não no runtime.
FROM node:20-alpine AS builder
WORKDIR /app

ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ARG NEXT_PUBLIC_API_URL

COPY package.json package-lock.json ./
# O lock é gerado no Windows e só grava a entrada instalável completa do binário
# nativo do win32 (lightningcss-win32-x64-msvc); os outros (linux-x64-musl etc.)
# ficam sem resolved/integrity. Por isso `npm install` lendo esse lock PULA o
# binário musl exigido pelo Tailwind v4 → "Cannot find module lightningcss...musl".
# Removemos o lock aqui para o npm re-resolver os optional deps nativos para a
# plataforma do builder (Alpine/musl). O lock do Windows continua commitado para
# o dev local — mantém a compatibilidade local ↔ VPS.
RUN rm -f package-lock.json && npm install

ENV NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL \
    NEXT_PUBLIC_SUPABASE_ANON_KEY=$NEXT_PUBLIC_SUPABASE_ANON_KEY \
    NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NODE_ENV=production

COPY . .
# next build lê output: 'standalone' do next.config.mjs e gera:
#   .next/standalone/ → server.js + node_modules mínimos
#   .next/static/     → assets estáticos (copiados separadamente abaixo)
RUN npm run build

# ── Stage 3: runtime ──────────────────────────────────────────────────────────
# Imagem final mínima: apenas o bundle standalone + assets estáticos.
# node_modules completo NÃO está aqui — o standalone já inclui o mínimo.
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

RUN addgroup --system nextjs && adduser --system --ingroup nextjs nextjs

# Assets estáticos públicos (imagens, favicon, etc.)
COPY --from=builder /app/public ./public

# Bundle standalone (server.js + node_modules necessários)
COPY --from=builder --chown=nextjs:nextjs /app/.next/standalone ./

# Assets estáticos compilados pelo Next (JS, CSS, chunks)
COPY --from=builder --chown=nextjs:nextjs /app/.next/static ./.next/static

USER nextjs
EXPOSE 3000

# server.js é o servidor HTTP mínimo gerado pelo output: 'standalone'.
CMD ["node", "server.js"]
