# GestãoAcademia

Sistema completo de gestão para academias, desenvolvido com foco em controle financeiro, gestão de alunos, relatórios e portal do aluno.

---

## Funcionalidades

### Painel Administrativo
- **Dashboard** com KPIs em tempo real: alunos ativos, inadimplentes, receita do mês, taxa de inadimplência e distribuição por plano
- **Gestão de alunos** com cadastro, edição, filtros por status (ativo, inativo, inadimplente) e busca por nome ou CPF
- **Gestão de mensalidades** com filtros por status e mês, registro de pagamento manual e cálculo automático de juros
- **Gestão de instrutores** com cadastro, edição e vinculação a planos
- **Gestão de planos** com ativação/desativação e edição inline
- **Relatórios exportáveis** em PDF e Excel (alunos, financeiro, inadimplência)
- **Notificações por e-mail** automáticas: aviso de vencimento (1 dia antes) e cobrança de mensalidades em atraso

### Portal do Aluno
- Visualização de dados pessoais e status da conta
- Histórico completo de mensalidades com detalhamento de juros
- Histórico de frequência (quando habilitado)

### Regras de Negócio
- Mensalidades geradas **automaticamente** a cada ciclo de plano ativo
- **Juros de 2% ao mês** calculados proporcionalmente por dia de atraso
- Aluno marcado como **inadimplente** automaticamente 1 dia após o vencimento
- Status restaurado para **ativo** ao quitar todas as pendências
- Controle de frequência **opcional** e configurável por aluno

---

## Stack Tecnológica

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.11 + Flask 3.0 |
| Frontend | Next.js (App Router) + Tailwind CSS v4 |
| Banco de dados |  (PostgreSQL) |
| Autenticação |  Auth (JWT) |
| Agendamento | APScheduler |
| PDF | ReportLab |
| Excel | openpyxl |
| E-mail | Gmail SMTP (smtplib) |
| Testes | pytest + unittest.mock |

---

## Arquitetura

```
gestao-academia/
├── backend/
│   ├── app/
│   │   ├── auth/          # Autenticação e middleware JWT
│   │   ├── alunos/        # CRUD de alunos e vínculos com planos
│   │   ├── instrutores/   # CRUD de instrutores e vínculos com planos
│   │   ├── planos/        # CRUD de planos
│   │   ├── mensalidades/  # Pagamentos, jobs de geração e inadimplência
│   │   ├── dashboard/     # KPIs e indicadores
│   │   ├── relatorios/    # Exportação PDF e Excel
│   │   ├── notificacoes/  # E-mails automáticos via SMTP
│   │   └── portal/        # Endpoints exclusivos do aluno
│   ├── tests/             # Testes unitários (47 casos)
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

Execute as migrations no **SQL Editor** do Supabase para criar as tabelas, enums, RLS policies e triggers. Consulte o `PLANEJAMENTO.md` para o schema completo.

---

## API — Visão Geral dos Endpoints

### Autenticação
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| POST | `/auth/login` | Login com e-mail e senha |
| POST | `/auth/logout` | Logout |
| GET | `/auth/me` | Perfil do usuário autenticado |

### Alunos
| Método | Endpoint | Descrição |
|--------|----------|-----------|
| GET | `/alunos` | Listar (filtros: `status`, `cpf`) |
| POST | `/alunos` | Cadastrar aluno |
| GET | `/alunos/:id` | Buscar aluno |
| PUT | `/alunos/:id` | Atualizar aluno |
| POST | `/alunos/:id/planos` | Vincular plano ao aluno |

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
| POST | `/mensalidades/:id/pagar` | Registrar pagamento |

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

---

## Testes

```bash
cd backend
python -m pytest -v
```

A suíte cobre **47 casos de teste** distribuídos entre autenticação, CRUD, regras de negócio (juros, inadimplência), notificações e portal do aluno.

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
- Validação de dados nas duas pontas: frontend e backend
- Variáveis sensíveis isoladas em `.env` e nunca commitadas

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
- [ ] Fase 9 — Integração de pagamentos (Stripe / PagSeguro)

---

## Licença

Este projeto é de uso privado. Todos os direitos reservados.
