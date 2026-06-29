# GestãoAcademia

Sistema completo de gestão para academias, desenvolvido com foco em controle financeiro, gestão de alunos, relatórios e portal do aluno.

---

## Funcionalidades

### Painel Administrativo
- **Dashboard** com KPIs em tempo real: alunos ativos, inadimplentes, receita do mês, taxa de inadimplência e distribuição por plano
- **Gestão de alunos** com cadastro, edição, foto (upload, webcam ou Gravatar), filtros por status (ativo, inativo, inadimplente) e busca por nome ou CPF
- **Gestão de vínculos de planos** por aluno: vincular, editar, cancelar e excluir vínculos, com bloqueio de plano ativo duplicado e detalhamento das mensalidades geradas
- **Gestão de mensalidades** com filtros por status e mês, registro de pagamento manual e cálculo automático de juros
- **Avaliações físicas** com medidas, dobras, diâmetros e exportação em PDF
- **Gestão de instrutores** com cadastro, edição e vinculação a planos
- **Gestão de planos** com ativação/desativação e edição inline
- **Configurações** de usuários do sistema (tipo/permissão, ativação) e dados da academia
- **Relatórios exportáveis** em PDF e Excel (alunos, financeiro, inadimplência)
- **Notificações por e-mail** automáticas: aviso de vencimento (1 dia antes) e cobrança de mensalidades em atraso

### Portal do Aluno
- Visualização de dados pessoais e status da conta
- Histórico completo de mensalidades com detalhamento de juros
- Histórico de frequência (quando habilitado)
- Avaliações físicas, ficha de treino e avisos

### Regras de Negócio
- Mensalidades geradas **automaticamente** a cada ciclo de plano ativo
- **Juros de 2% ao mês** calculados proporcionalmente por dia de atraso
- Aluno marcado como **inadimplente** automaticamente 1 dia após o vencimento
- Status restaurado para **ativo** ao quitar todas as pendências
- Controle de frequência **opcional** e configurável por aluno
- **Unicidade garantida**: um aluno não pode ter o mesmo plano ativo duplicado e não há mensalidades duplicadas por vínculo/vencimento — validado no backend e por índices únicos parciais no banco (migration `011`)

---

## Stack Tecnológica

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.11 + Flask 3.0 |
| Frontend | Next.js (App Router) + Tailwind CSS v4 |
| Banco de dados | Supabase (PostgreSQL) com RLS |
| Autenticação | Supabase Auth (JWT) |
| Imagens / avatares | Pillow + Supabase Storage |
| Agendamento | APScheduler |
| PDF | ReportLab |
| Excel | openpyxl |
| E-mail | Gmail SMTP (smtplib) |
| Validação | Pydantic |
| Testes | pytest + unittest.mock |

---

## Arquitetura

```
gestao-academia/
├── backend/
│   ├── app/
│   │   ├── auth/          # Autenticação, middleware JWT e avatares
│   │   ├── alunos/        # CRUD de alunos e gestão de vínculos com planos
│   │   ├── instrutores/   # CRUD de instrutores e vínculos com planos
│   │   ├── planos/        # CRUD de planos
│   │   ├── mensalidades/  # Pagamentos, jobs de geração e inadimplência
│   │   ├── avaliacoes/    # Avaliações físicas e exportação PDF
│   │   ├── configuracoes/ # Usuários do sistema e dados da academia
│   │   ├── dashboard/     # KPIs e indicadores
│   │   ├── relatorios/    # Exportação PDF e Excel
│   │   ├── notificacoes/  # E-mails automáticos via SMTP
│   │   └── portal/        # Endpoints exclusivos do aluno
│   ├── migrations/        # Migrations SQL versionadas (001–011)
│   ├── tests/             # Testes unitários (185 casos)
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── admin/         # Painel administrativo (layout + páginas)
│   │   ├── login/         # Tela de login unificada
│   │   └── frequencia/    # Histórico de frequência (portal)
│   ├── components/        # Componentes reutilizáveis
│   └── lib/               # Cliente Supabase e funções de API
└── README.md
```

### Tipos de Usuário e Permissões

| Tipo | Acesso |
|------|--------|
| `admin` | Acesso total ao sistema |
| `recepcionista` | Alunos, mensalidades, frequência e relatórios |
| `instrutor` | Visualização dos alunos vinculados aos seus planos |
| `aluno` | Portal próprio — dados pessoais, mensalidades e frequência |

---

## Configuração do Ambiente

### Pré-requisitos

- Python 3.11+
- Node.js 18+
- Conta no [Supabase](https://supabase.com)

### 1. Clone o repositório

```bash
git clone https://github.com/seu-usuario/gestao-academia.git
cd gestao-academia
```

### 2. Configure as variáveis de ambiente

Crie o arquivo `.env` na raiz do projeto:

```env
# Supabase
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_ANON_KEY=sua_anon_key
SUPABASE_SERVICE_ROLE_KEY=sua_service_role_key
SUPABASE_JWT_SECRET=seu_jwt_secret

# Banco de dados
DB_PASSWORD=sua_senha_do_banco

# E-mail (Gmail SMTP)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USER=seu@gmail.com
EMAIL_PASSWORD=sua_senha_de_app
EMAIL_FROM=seu@gmail.com
```

> **Importante:** Nunca exponha o `.env` em repositórios públicos. O arquivo já está no `.gitignore`.

### 3. Backend

```bash
cd backend
pip install -r requirements.txt
python -m flask run
```

O servidor estará disponível em `http://localhost:5000`.

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

A aplicação estará disponível em `http://localhost:3000`.

### 5. Banco de dados

Execute as migrations da pasta `backend/migrations/` (arquivos `001` a `011`), **em ordem**, no **SQL Editor** do Supabase para criar tabelas, enums, RLS policies, triggers e os índices de unicidade. As migrations são versionadas e idempotentes — rode-as manualmente, pois o projeto não possui runner automático.

---

## API — Visão Geral dos Endpoints

### Autenticação
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/auth/login` | Login com e-mail e senha |
| POST | `/auth/logout` | Logout |
| GET | `/auth/me` | Perfil do usuário autenticado |
| PUT | `/auth/me` | Atualizar perfil |
| POST | `/auth/change-password` | Alterar senha |
| POST | `/auth/me/avatar` | Enviar foto de perfil |
| DELETE | `/auth/me/avatar` | Remover foto de perfil |
| POST | `/auth/me/avatar/gravatar` | Usar Gravatar como foto |

### Alunos
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/alunos` | Listar (filtros: `status`, `cpf`) |
| POST | `/alunos` | Cadastrar aluno |
| GET | `/alunos/:id` | Buscar aluno |
| PUT | `/alunos/:id` | Atualizar aluno |
| PATCH | `/alunos/:id/status` | Alterar status do aluno |
| GET | `/alunos/:id/planos` | Listar vínculos de planos do aluno |
| POST | `/alunos/:id/planos` | Vincular plano (bloqueia plano ativo duplicado) |
| GET | `/alunos/:id/planos/:vinculo_id` | Detalhe do vínculo + mensalidades |
| PUT | `/alunos/:id/planos/:vinculo_id` | Editar vínculo (datas/status) |
| DELETE | `/alunos/:id/planos/:vinculo_id` | Cancelar vínculo (ou `?permanente=true` para excluir) |

### Instrutores
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/instrutores` | Listar instrutores |
| POST | `/instrutores` | Cadastrar instrutor |
| GET | `/instrutores/:id` | Buscar instrutor |
| PUT | `/instrutores/:id` | Atualizar instrutor |
| POST | `/instrutores/:id/planos` | Vincular plano |
| DELETE | `/instrutores/:id/planos/:ip_id` | Desvincular plano |

### Planos
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/planos` | Listar planos |
| POST | `/planos` | Criar plano |
| PUT | `/planos/:id` | Atualizar plano |
| PATCH | `/planos/:id/ativo` | Ativar/desativar plano |

### Mensalidades
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/mensalidades` | Listar (filtros: `status`, `mes`, `aluno_id`) |
| GET | `/mensalidades/:id` | Buscar mensalidade |
| POST | `/mensalidades/:id/pagar` | Registrar pagamento |

### Avaliações Físicas
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/avaliacoes` | Listar (paginado: `limit`, `offset`) |
| POST | `/avaliacoes` | Criar avaliação |
| GET | `/avaliacoes/:id` | Buscar avaliação |
| PUT | `/avaliacoes/:id` | Atualizar avaliação |
| DELETE | `/avaliacoes/:id` | Excluir avaliação |
| GET | `/avaliacoes/:id/pdf` | Exportar avaliação em PDF |

### Configurações
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/configuracoes/usuarios` | Listar usuários do sistema |
| PATCH | `/configuracoes/usuarios/:id/tipo` | Alterar tipo/permissão |
| PATCH | `/configuracoes/usuarios/:id/status` | Ativar/desativar usuário |
| POST | `/configuracoes/usuarios/:id/avatar` | Definir foto de outro usuário |
| DELETE | `/configuracoes/usuarios/:id/avatar` | Remover foto de outro usuário |
| GET | `/configuracoes/academia` | Dados da academia |
| PUT | `/configuracoes/academia` | Atualizar dados da academia |

### Dashboard
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/dashboard/alunos` | KPIs de alunos |
| GET | `/dashboard/financeiro` | KPIs financeiros do mês |
| GET | `/dashboard/frequencia` | KPIs de frequência |

### Relatórios
| Método | Endpoint | Parâmetros |
|--------|----------|-----------|
| GET | `/relatorios/alunos` | `formato=pdf\|excel`, `status` |
| GET | `/relatorios/financeiro` | `formato=pdf\|excel`, `mes=YYYY-MM` |
| GET | `/relatorios/inadimplencia` | `formato=pdf\|excel` |

### Portal do Aluno
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/portal/me` | Dados do aluno autenticado |
| GET | `/portal/mensalidades` | Mensalidades do aluno |
| GET | `/portal/frequencias` | Histórico de frequência |
| GET | `/portal/avaliacoes` | Avaliações físicas do aluno |
| GET | `/portal/treino` | Ficha de treino do aluno |
| GET | `/portal/avisos` | Avisos direcionados ao aluno |

---

## Testes

```bash
cd backend
python -m pytest -v
```

A suíte cobre **185 casos de teste** distribuídos entre autenticação, avatares, CRUD, gestão de vínculos de planos, unicidade de planos/mensalidades, avaliações físicas, regras de negócio (juros, inadimplência), configurações, notificações e portal do aluno.

---

## Jobs Agendados

| Horário | Job | Descrição |
|---------|-----|-----------|
| 00:05 | `job_atualizar_inadimplencia` | Marca mensalidades vencidas como `atrasada` e atualiza status dos alunos |
| 00:10 | `job_gerar_mensalidades` | Gera a próxima mensalidade para planos com vencimento em 5 dias |
| 08:00 | `job_notificar_vencimentos` | E-mail para alunos com mensalidade vencendo amanhã |
| 08:15 | `job_notificar_atrasadas` | E-mail para alunos com mensalidades em atraso |

---

## Segurança

- Autenticação via **JWT validado pelo Supabase Auth** em todas as rotas protegidas
- **RLS (Row Level Security)** no PostgreSQL por tipo de usuário
- **Service Role Key** usada exclusivamente no backend (nunca exposta ao cliente)
- **Rate limiting** (Flask-Limiter) nas rotas sensíveis, como o login
- **CORS** restrito às origens configuradas
- Validação de dados nas duas pontas: frontend (React) e backend (Pydantic)
- Variáveis sensíveis isoladas em `.env` e nunca commitadas

---

## Deploy / Produção

O deploy de produção roda em uma **VPS com Docker**, orquestrado por um **`docker-compose.yml`** que builda as imagens a partir dos `Dockerfile` de cada serviço (imagens base **Alpine** leves, multi-stage):

- **Backend** Flask servido por **gunicorn** (não o dev server)
- **Frontend** Next.js em modo produção (`next build && next start`)
- **Supabase** é gerenciado (banco na nuvem) — fica **fora** do compose, conectado via URL + chaves no `.env`

Na borda, um **Nginx** na VPS atua como proxy reverso apontando para os containers, e o **Cloudflare** está na frente (DNS + TLS). Lembre-se de configurar `ProxyFix` no Flask para que `X-Forwarded-For`/`X-Forwarded-Proto` sejam lidos corretamente na cadeia Cloudflare → Nginx → container.

> Os artefatos de produção (`docker-compose.yml`, `Dockerfile`s) são montados sob demanda — ainda não versionados neste estágio.

---

## Roadmap

- [x] Fase 1 — Estrutura base, schema e migrations
- [x] Fase 2 — Autenticação e controle de acesso
- [x] Fase 3 — CRUD principal (alunos, instrutores, planos)
- [x] Fase 4 — Mensalidades automáticas e juros
- [x] Fase 5 — Dashboards
- [x] Fase 6 — Relatórios PDF e Excel
- [x] Fase 7 — Notificações por e-mail
- [x] Fase 8 — Portal do aluno (Next.js)
- [x] Fase 9 — Avaliações físicas, fichas de treino e avisos
- [x] Fase 10 — Avatares (upload, webcam e Gravatar)
- [x] Fase 11 — Configurações (usuários do sistema e academia)
- [x] Fase 12 — Unicidade de planos/mensalidades (backend + índices no banco)
- [ ] Fase 13 — Containerização e deploy em produção (Docker Compose + Nginx)
- [ ] Fase 14 — Integração de pagamentos (Stripe / PagSeguro)

---

## Licença

Este projeto é de uso privado. Todos os direitos reservados.
