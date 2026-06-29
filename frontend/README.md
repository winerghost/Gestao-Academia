# GestãoAcademia — Frontend

Interface web do **GestãoAcademia**, construída com **Next.js (App Router)** e **Tailwind CSS v4**. Entrega o painel administrativo (admin, recepcionista, instrutor) e o portal do aluno.

> ⚠️ Esta versão do Next.js tem breaking changes. Antes de escrever código específico de Next.js, consulte `node_modules/next/dist/docs/` (ver `AGENTS.md`).

## Pré-requisitos

- Node.js 18+
- Backend Flask rodando (ver `../README.md` na raiz)

## Configuração

Crie um `.env.local` na pasta `frontend/` com as variáveis públicas do Supabase e a URL da API:

```env
NEXT_PUBLIC_SUPABASE_URL=https://seu-projeto.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=sua_anon_key
NEXT_PUBLIC_API_URL=http://localhost:5000
```

## Desenvolvimento

```bash
npm install
npm run dev      # http://localhost:3000
```

Outros scripts:

```bash
npm run build    # build de produção
npm run start    # serve o build de produção
npm run lint     # ESLint
```

## Estrutura

```
frontend/
├── app/
│   ├── admin/        # Painel administrativo (layout + páginas)
│   ├── login/        # Tela de login unificada
│   └── frequencia/   # Histórico de frequência (portal)
├── components/       # Componentes reutilizáveis
└── lib/              # Cliente Supabase e funções de API (api.js)
```

A autenticação usa **Supabase Auth (JWT)**; o token é enviado nas chamadas à API Flask. A validação de dados é feita nas **duas pontas** (frontend e backend).
