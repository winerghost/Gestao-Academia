# ── Stage 1: dependências ─────────────────────────────────────────────────────
# Instala apenas as dependências de produção (--omit=dev) para o stage final.
FROM node:20-alpine AS deps
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# ── Stage 2: build ────────────────────────────────────────────────────────────
# Compila o Next.js com todas as devDependencies (TypeScript, tailwind, etc.).
# ARGs: variáveis públicas do Next.js (NEXT_PUBLIC_*) são embutidas no bundle
# em build time — precisam estar disponíveis aqui, não no runtime.
FROM node:20-alpine AS builder
WORKDIR /app

ARG NEXT_PUBLIC_SUPABASE_URL
ARG NEXT_PUBLIC_SUPABASE_ANON_KEY
ARG NEXT_PUBLIC_API_URL

ENV NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL \
    NEXT_PUBLIC_SUPABASE_ANON_KEY=$NEXT_PUBLIC_SUPABASE_ANON_KEY \
    NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NODE_ENV=production

COPY package.json package-lock.json ./
RUN npm ci

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
