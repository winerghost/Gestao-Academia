# -*- coding: utf-8 -*-
"""Gera o guia de deploy (PDF) da aplicação Gestão de Academias na VPS Hostinger.

Cobre:
  - Arquitetura de produção (serviços, rede, Cloudflare)
  - Pré-requisitos na VPS
  - Passo a passo: clone → .env → build → verificação
  - Referência completa das variáveis de ambiente
  - Configuração do Cloudflare (DNS + SSL)
  - Checklist pós-deploy e comandos de manutenção

Execute:
    cd backend
    python scripts/gerar_doc_deploy.py
    # gera GUIA_DEPLOY.pdf na raiz do projeto
"""
import os
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether,
)

_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SAIDA = os.path.join(_RAIZ, "GUIA_DEPLOY.pdf")

# ── Paleta de cores ───────────────────────────────────────────────────────────
AZUL   = colors.HexColor("#1e3a5f")
AZUL2  = colors.HexColor("#2c5282")
AZUL_L = colors.HexColor("#ebf4ff")
CINZA  = colors.HexColor("#4a5568")
CINZAC = colors.HexColor("#edf2f7")
VERDE  = colors.HexColor("#276749")
VERDE_L= colors.HexColor("#f0fff4")
LARAN  = colors.HexColor("#c05621")
AMAR_L = colors.HexColor("#fffff0")
MONO   = colors.HexColor("#2d3748")

# ── Estilos ───────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

def S(name, **kw):
    styles.add(ParagraphStyle(name, **kw))

S("Capa",     fontName="Helvetica-Bold", fontSize=24, leading=30, textColor=AZUL,  alignment=TA_CENTER)
S("CapaSub",  fontName="Helvetica",      fontSize=12, leading=18, textColor=CINZA, alignment=TA_CENTER)
S("H1",       fontName="Helvetica-Bold", fontSize=15, leading=20, textColor=AZUL,  spaceBefore=14, spaceAfter=6)
S("H2",       fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=AZUL2, spaceBefore=10, spaceAfter=4)
S("H3",       fontName="Helvetica-Bold", fontSize=10, leading=14, textColor=MONO,  spaceBefore=8, spaceAfter=3)
S("Corpo",    fontName="Helvetica",      fontSize=9.5, leading=14, textColor=MONO,  alignment=TA_JUSTIFY, spaceAfter=4)
S("CorpoP",   fontName="Helvetica",      fontSize=9,   leading=13, textColor=MONO)
S("Mono",     fontName="Courier",        fontSize=8.5, leading=13, textColor=MONO)
S("MonoB",    fontName="Courier-Bold",   fontSize=8.5, leading=13, textColor=AZUL)
S("Cel",      fontName="Helvetica",      fontSize=8,   leading=11, textColor=MONO)
S("CelB",     fontName="Helvetica-Bold", fontSize=8,   leading=11, textColor=colors.white)
S("CelM",     fontName="Courier",        fontSize=7.8, leading=11, textColor=MONO)
S("Nota",     fontName="Helvetica-Oblique", fontSize=8.5, leading=13, textColor=CINZA, spaceAfter=4)
S("Rodape",   fontName="Helvetica",      fontSize=7.5, leading=10, textColor=CINZA, alignment=TA_CENTER)
S("Passo",    fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=colors.white, alignment=TA_CENTER)

_RealParagraph = Paragraph
def Paragraph(text, style=None, **kw):
    if isinstance(style, str):
        style = styles[style]
    return _RealParagraph(text, style, **kw)

el = []

def p(txt, st="Corpo"):    el.append(Paragraph(txt, styles[st]))
def sp(h=6):               el.append(Spacer(1, h))
def hr():                  el.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e0"), spaceBefore=4, spaceAfter=6))
def pb():                  el.append(PageBreak())

def passo(num, titulo, cor=AZUL2):
    """Cabeçalho numerado de passo (badge colorido + título)."""
    row = Table(
        [[Paragraph(str(num), "Passo"), Paragraph(f" {titulo}", "H2")]],
        colWidths=[0.9*cm, 14.1*cm]
    )
    row.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,0), cor),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ("LEFTPADDING",(1,0), (1,0), 6),
    ]))
    el.append(KeepTogether([sp.__self__.__class__(1, 8) if hasattr(sp, '__self__') else Spacer(1, 8), row]))

def cmd(texto):
    """Bloco de comando no terminal (fundo cinza, fonte mono)."""
    tbl = Table([[Paragraph(texto, styles["Mono"])]], colWidths=[15*cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), CINZAC),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LINEBELOW", (0,0), (-1,-1), 0.3, colors.HexColor("#a0aec0")),
    ]))
    el.append(tbl)
    sp(3)

def nota(texto):
    """Nota de atenção com ícone."""
    tbl = Table(
        [[Paragraph("⚠", styles["H2"]), Paragraph(texto, styles["Corpo"])]],
        colWidths=[0.7*cm, 14.3*cm]
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), AMAR_L),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LINEBELOW", (0,0), (-1,-1), 0.3, colors.HexColor("#d69e2e")),
    ]))
    el.append(tbl)
    sp(4)

def dica(texto):
    """Dica verde."""
    tbl = Table(
        [[Paragraph("✓", styles["H2"]), Paragraph(texto, styles["Corpo"])]],
        colWidths=[0.7*cm, 14.3*cm]
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), VERDE_L),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LINEBELOW", (0,0), (-1,-1), 0.3, colors.HexColor("#9ae6b4")),
    ]))
    el.append(tbl)
    sp(4)

# ══════════════════════════════════════════════════════════════════════════════
# CAPA
# ══════════════════════════════════════════════════════════════════════════════
sp(100)
p("Guia de Deploy em Produção", "Capa")
sp(4)
p("Sistema de Gestão de Academias", "CapaSub")
p("VPS Hostinger + Docker Compose + Cloudflare", "CapaSub")
sp(30)
meta = Table([
    ["Aplicação",    "Flask (API) + Next.js (Frontend) + Redis + Nginx"],
    ["Infraestrutura","VPS Hostinger (Ubuntu 22.04) com Docker Compose"],
    ["Borda",        "Cloudflare CDN/DNS/TLS (modo Full SSL)"],
    ["Banco",        "Supabase gerenciado (fora do Compose)"],
    ["Data",         date.today().strftime("%d/%m/%Y")],
    ["Versão",       "1.0 — gerado automaticamente por scripts/gerar_doc_deploy.py"],
], colWidths=[3.5*cm, 11.5*cm])
meta.setStyle(TableStyle([
    ("FONTNAME",  (0,0), (0,-1), "Helvetica-Bold"),
    ("FONTNAME",  (1,0), (1,-1), "Helvetica"),
    ("FONTSIZE",  (0,0), (-1,-1), 9),
    ("TEXTCOLOR", (0,0), (0,-1), AZUL),
    ("TEXTCOLOR", (1,0), (1,-1), CINZA),
    ("LINEBELOW", (0,0), (-1,-2), 0.4, colors.HexColor("#e2e8f0")),
    ("TOPPADDING",    (0,0), (-1,-1), 5),
    ("BOTTOMPADDING", (0,0), (-1,-1), 5),
]))
el.append(meta)
sp(40)
p("Documento técnico — uso interno do projeto.", "Rodape")
pb()

# ══════════════════════════════════════════════════════════════════════════════
# 1. ARQUITETURA
# ══════════════════════════════════════════════════════════════════════════════
p("1. Arquitetura de Produção", "H1")
hr()
p("O sistema é composto por 4 serviços Docker na VPS, com o Supabase gerenciado "
  "externamente (não entra no Compose). O Cloudflare fica na borda como CDN, "
  "DNS e terminador TLS — a VPS recebe apenas tráfego HTTP de IPs do Cloudflare.", "Corpo")
sp(4)

arq = Table([
    [Paragraph("Serviço", "CelB"), Paragraph("Imagem / Build", "CelB"),
     Paragraph("Porta interna", "CelB"), Paragraph("Função", "CelB")],
    ["nginx",    "nginx:1.27-alpine (imagem oficial)",    "80 / 443 (host)", "Proxy reverso. Roteia /api/* → Flask, /* → Next.js. Servidores estáticos em cache."],
    ["frontend", "Build multi-stage Node 20-alpine",      "3000 (interno)",  "Next.js standalone. Serve SSR e assets estáticos. NEXT_PUBLIC_* embutidos no build."],
    ["backend",  "Build multi-stage Python 3.11-alpine",  "5000 (interno)",  "Flask via gunicorn. API REST. APScheduler (notificações). Conecta ao Supabase e ao Redis."],
    ["redis",    "redis:7-alpine (imagem oficial)",        "6379 (interno)",  "Rate limiting compartilhado (Flask-Limiter) e lock do APScheduler (evita e-mails duplicados)."],
], colWidths=[2.0*cm, 3.8*cm, 2.8*cm, 6.4*cm], repeatRows=1)
arq.setStyle(TableStyle([
    ("BACKGROUND",    (0,0),  (-1,0), AZUL),
    ("VALIGN",        (0,0),  (-1,-1), "TOP"),
    ("FONTNAME",      (0,1),  (-1,-1), "Helvetica"),
    ("FONTSIZE",      (0,1),  (-1,-1), 7.8),
    ("TEXTCOLOR",     (0,1),  (-1,-1), MONO),
    ("GRID",          (0,0),  (-1,-1), 0.4, colors.HexColor("#cbd5e0")),
    ("ROWBACKGROUNDS",(0,1),  (-1,-1), [colors.white, CINZAC]),
    ("TOPPADDING",    (0,0),  (-1,-1), 4),
    ("BOTTOMPADDING", (0,0),  (-1,-1), 4),
    ("LEFTPADDING",   (0,0),  (-1,-1), 5),
    ("FONTNAME",      (0,1),  (0,-1), "Courier"),
]))
el.append(arq)
sp(8)

p("Fluxo de requisição:", "H2")
fluxo_itens = [
    "Usuário acessa <font face='Courier'>https://academia.seudominio.com.br</font>",
    "Cloudflare termina TLS e repassa HTTP para a VPS na porta 80",
    "Nginx decide: <font face='Courier'>/api/*</font> vai para Flask (porta 5000); todo o resto vai para Next.js (porta 3000)",
    "Next.js renderiza a página (SSR ou cached) e retorna ao browser",
    "JavaScript do browser faz fetch para <font face='Courier'>/api/auth/login</font> etc. — mesma origem, sem CORS",
    "Flask autentica via Supabase Auth e acessa o banco via Supabase SDK",
]
for i, item in enumerate(fluxo_itens, 1):
    el.append(Paragraph(f"{i}. {item}", styles["CorpoP"]))
    sp(2)

sp(6)
nota("O prefixo <font face='Courier'>/api/</font> é removido pelo nginx antes de repassar ao Flask. "
     "Exemplo: <font face='Courier'>GET /api/auth/login → GET /auth/login</font> (Flask nunca vê o prefixo). "
     "Por isso o <font face='Courier'>NEXT_PUBLIC_API_URL</font> em produção é <font face='Courier'>https://seudominio.com/api</font> "
     "(com /api), mas as rotas do Flask não precisam de prefixo.")
pb()

# ══════════════════════════════════════════════════════════════════════════════
# 2. PRÉ-REQUISITOS
# ══════════════════════════════════════════════════════════════════════════════
p("2. Pré-requisitos na VPS Hostinger", "H1")
hr()
p("Todos os comandos abaixo são executados via SSH na VPS como root ou usuário sudo.", "Corpo")
sp(4)

p("2.1 Sistema operacional", "H2")
p("Ubuntu 22.04 LTS (recomendado na Hostinger). Verifique:", "CorpoP")
cmd("lsb_release -a")

p("2.2 Docker e Docker Compose v2", "H2")
p("Instale Docker Engine + plugin Compose (v2) com o script oficial:", "CorpoP")
cmd("curl -fsSL https://get.docker.com | sh")
cmd("docker --version && docker compose version")
nota("O script acima instala o Docker Engine e o plugin <font face='Courier'>compose</font>. "
     "Verifique que o output é <font face='Courier'>Docker Compose version v2.x.x</font> (não v1). "
     "Se aparecer <font face='Courier'>docker-compose</font> (com hífen) ainda é a versão v1 — "
     "remova e reinstale.")

p("2.3 Git", "H2")
cmd("apt-get update && apt-get install -y git")

p("2.4 Firewall (UFW)", "H2")
p("Libere apenas as portas necessárias. Cloudflare se conecta nas portas 80 e 443.", "CorpoP")
cmd("ufw allow 22/tcp\nufw allow 80/tcp\nufw allow 443/tcp\nufw enable\nufw status")
dica("Feche a porta 5000 (Flask), 3000 (Next.js) e 6379 (Redis) — esses serviços "
     "comunicam apenas dentro da rede Docker interna (não precisam ser expostos).")

p("2.5 Configuração do Supabase", "H2")
reqs_supa = [
    "Bucket de Storage criado com o nome definido em <font face='Courier'>AVATAR_BUCKET</font> (padrão: <font face='Courier'>avatars</font>) — marcar como <b>público</b>.",
    "Migrations executadas em ordem no SQL Editor do Supabase (pasta <font face='Courier'>backend/migrations/</font>, arquivos 001 a 011).",
    "E-mail de notificação configurado no painel Supabase Auth (opcional, mas recomendado).",
    "Chaves copiadas: <font face='Courier'>SUPABASE_URL</font>, <font face='Courier'>SUPABASE_ANON_KEY</font> e <font face='Courier'>SUPABASE_SERVICE_ROLE_KEY</font> do painel Project Settings → API.",
]
for r in reqs_supa:
    el.append(Paragraph(f"• {r}", styles["CorpoP"]))
    sp(2)
pb()

# ══════════════════════════════════════════════════════════════════════════════
# 3. PASSO A PASSO
# ══════════════════════════════════════════════════════════════════════════════
p("3. Deploy Passo a Passo", "H1")
hr()

sp(6)
passo(1, "Clonar o repositório na VPS")
sp(4)
p("Escolha um diretório de trabalho (ex.: <font face='Courier'>/opt/academia</font>) e clone:", "CorpoP")
cmd("mkdir -p /opt/academia && cd /opt/academia\ngit clone https://github.com/SEU_USUARIO/gestao-academia.git .\n# ou com SSH:\ngit clone git@github.com:SEU_USUARIO/gestao-academia.git .")
nota("Substitua o URL pelo repositório real. Se o projeto for privado, configure "
     "uma deploy key no GitHub: <font face='Courier'>ssh-keygen -t ed25519 -C 'deploy@vps'</font> e "
     "adicione a chave pública em Settings → Deploy Keys.")

sp(6)
passo(2, "Criar e preencher o arquivo .env")
sp(4)
p("O <font face='Courier'>docker-compose.yml</font> lê todas as variáveis de um único "
  "<font face='Courier'>.env</font> na raiz do projeto:", "CorpoP")
cmd("cd /opt/academia\ncp .env.production.example .env\nnano .env")
p("Preencha os campos marcados com <font face='Courier'>PREENCHER</font>. Os mínimos obrigatórios são:", "CorpoP")
sp(3)
minimos = [
    ("<font face='Courier'>FRONTEND_URL</font>", "URL pública completa, ex.: <font face='Courier'>https://academia.seudominio.com.br</font>"),
    ("<font face='Courier'>SUPABASE_URL</font>", "URL do projeto Supabase"),
    ("<font face='Courier'>SUPABASE_ANON_KEY</font>", "Chave pública anon"),
    ("<font face='Courier'>SUPABASE_SERVICE_ROLE_KEY</font>", "Chave secreta service_role (nunca versionar)"),
    ("<font face='Courier'>EMAIL_USER</font> / <font face='Courier'>EMAIL_PASSWORD</font>", "Conta Gmail + senha de app (16 chars)"),
]
tbl_min = Table(minimos, colWidths=[4.5*cm, 10.5*cm])
tbl_min.setStyle(TableStyle([
    ("FONTSIZE", (0,0), (-1,-1), 8),
    ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
    ("GRID", (0,0), (-1,-1), 0.4, colors.HexColor("#e2e8f0")),
    ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, CINZAC]),
    ("TOPPADDING", (0,0), (-1,-1), 4),
    ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ("LEFTPADDING", (0,0), (-1,-1), 5),
]))
el.append(tbl_min)
sp(4)
nota("A variável <font face='Courier'>SUPABASE_SERVICE_ROLE_KEY</font> permite acesso total ao banco "
     "(ignora RLS). Nunca compartilhe, versione ou imprima nos logs. "
     "No .gitignore, verifique que <font face='Courier'>.env</font> (sem sufixo) está na lista.")

sp(6)
passo(3, "Build e start dos containers")
sp(4)
p("Na raiz do projeto (onde está o <font face='Courier'>docker-compose.yml</font>):", "CorpoP")
cmd("cd /opt/academia\ndocker compose up -d --build")
p("O primeiro build leva 5–10 minutos (baixa imagens base, compila Python e Next.js). "
  "Builds subsequentes são muito mais rápidos (cache de layers).", "CorpoP")
sp(4)
dica("Se o build do frontend falhar com 'out of memory', adicione swap na VPS: "
     "<font face='Courier'>fallocate -l 2G /swapfile && chmod 600 /swapfile && mkswap /swapfile && swapon /swapfile</font>")

sp(6)
passo(4, "Verificar os serviços")
sp(4)
cmd("docker compose ps\ndocker compose logs --tail=50 backend\ndocker compose logs --tail=50 frontend")
p("Todos os serviços devem aparecer como <font face='Courier'>healthy</font> ou <font face='Courier'>running</font>. "
  "O healthcheck do backend checa <font face='Courier'>GET /health</font>; o do frontend checa "
  "se o servidor retorna HTML na raiz.", "CorpoP")
cmd("# Teste rápido: deve retornar {\"status\": \"ok\"}\ncurl http://localhost/api/health")
pb()

sp(6)
passo(5, "Configurar DNS no Cloudflare")
sp(4)
dns_steps = [
    "Faça login em <b>dash.cloudflare.com</b> e selecione seu domínio.",
    "Vá em <b>DNS → Records</b> e adicione um registro <b>A</b>: Nome = <font face='Courier'>academia</font> (ou <font face='Courier'>@</font>), "
    "Valor = IP público da VPS Hostinger, Proxy = <b>Laranja (Proxied)</b>.",
    "Vá em <b>SSL/TLS → Overview</b> e selecione modo <b>Full</b> (ou Full Strict se tiver certificado Origin).",
    "Em <b>SSL/TLS → Edge Certificates</b>, ative <b>Always Use HTTPS</b> e <b>Automatic HTTPS Rewrites</b>.",
    "(Opcional) Em <b>Security → WAF</b>, ative as regras gerenciadas para proteção extra.",
    "Aguarde a propagação DNS (geralmente < 5 minutos com Cloudflare).",
]
for i, step in enumerate(dns_steps, 1):
    el.append(Paragraph(f"{i}. {step}", styles["CorpoP"]))
    sp(2)
sp(4)
nota("Modo Cloudflare <b>Full</b> (não Flexible): a conexão Cloudflare ↔ VPS é HTTPS, "
     "mas com certificado autoassinado. Para <b>Full Strict</b>, gere um certificado "
     "Cloudflare Origin em SSL/TLS → Origin Server e monte em <font face='Courier'>nginx/ssl/</font>.")
dica("Com Cloudflare Proxied ativado, a VPS fica protegida atrás dos IPs do Cloudflare. "
     "Adicione as regras de firewall da Hostinger para aceitar apenas os IPs do Cloudflare "
     "nas portas 80/443 para máxima proteção.")

sp(6)
passo(6, "Criar o primeiro usuário admin")
sp(4)
p("Com o backend rodando, crie o primeiro usuário admin diretamente no Supabase:", "CorpoP")
cad_steps = [
    "Painel Supabase → Authentication → Users → <b>Add user</b>: e-mail e senha do admin.",
    "SQL Editor do Supabase — execute o SQL abaixo para criar o perfil admin:",
]
for step in cad_steps:
    el.append(Paragraph(f"• {step}", styles["CorpoP"]))
    sp(2)
cmd("INSERT INTO public.profiles (id, nome, tipo, ativo)\nSELECT id, email, 'admin', true\nFROM auth.users\nWHERE email = 'admin@academia.com.br';")
p("Substitua o e-mail pelo que foi cadastrado no passo anterior. "
  "Os demais usuários (recepcionista, instrutor) podem ser criados via "
  "<font face='Courier'>POST /configuracoes/usuarios</font> pela interface web.", "CorpoP")
pb()

# ══════════════════════════════════════════════════════════════════════════════
# 4. REFERÊNCIA DE VARIÁVEIS DE AMBIENTE
# ══════════════════════════════════════════════════════════════════════════════
p("4. Referência Completa de Variáveis de Ambiente", "H1")
hr()
p("Todas as variáveis ficam em um único <font face='Courier'>.env</font> na raiz do projeto. "
  "O <font face='Courier'>docker-compose.yml</font> injeta cada variável no serviço correto.", "Corpo")
sp(6)

def tabela_env(titulo, linhas):
    p(titulo, "H2")
    tbl = Table(
        [[Paragraph("Variável", "CelB"), Paragraph("Padrão / Exemplo", "CelB"), Paragraph("Descrição", "CelB")]] + [
            [Paragraph(v, styles["CelM"]), Paragraph(e, styles["CelM"]), Paragraph(d, styles["Cel"])]
            for v, e, d in linhas
        ],
        colWidths=[4.8*cm, 3.8*cm, 6.4*cm], repeatRows=1
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0),  (-1,0), AZUL),
        ("GRID",          (0,0),  (-1,-1), 0.4, colors.HexColor("#cbd5e0")),
        ("ROWBACKGROUNDS",(0,1),  (-1,-1), [colors.white, CINZAC]),
        ("VALIGN",        (0,0),  (-1,-1), "TOP"),
        ("TOPPADDING",    (0,0),  (-1,-1), 4),
        ("BOTTOMPADDING", (0,0),  (-1,-1), 4),
        ("LEFTPADDING",   (0,0),  (-1,-1), 5),
    ]))
    el.append(tbl)
    sp(8)

tabela_env("4.1 Geral", [
    ("FRONTEND_URL",   "https://academia.seudominio.com", "URL pública do frontend. Usada no CORS (Flask) e para derivar NEXT_PUBLIC_API_URL."),
])

tabela_env("4.2 Supabase", [
    ("SUPABASE_URL",              "https://xxx.supabase.co", "URL do projeto. Painel → Project Settings → API."),
    ("SUPABASE_ANON_KEY",         "eyJ...",                  "Chave pública. Segura para ir ao frontend (embutida no build)."),
    ("SUPABASE_SERVICE_ROLE_KEY", "eyJ...",                  "⚠ SECRETA. Bypassa RLS. Apenas no backend. Nunca versionar."),
    ("SUPABASE_JWT_SECRET",       "(vazio)",                 "Opcional. JWT secret do Supabase. Não usado atualmente para validação local."),
])

tabela_env("4.3 Gunicorn / Performance", [
    ("WEB_CONCURRENCY", "2",    "Nº de workers gunicorn. Regra: 2 × nº CPUs + 1. Com 1 CPU: use 2."),
])

tabela_env("4.4 Rate Limiting", [
    ("RATELIMIT_DEFAULT", "200 per minute",              "Limite global por IP/token. Redis compartilha entre workers."),
    ("RATELIMIT_LOGIN",   "10 per minute;50 per hour",  "Limite específico do /auth/login (anti brute-force)."),
])

tabela_env("4.5 Avatares", [
    ("AVATAR_BUCKET",    "avatars",   "Nome do bucket no Supabase Storage (deve ser público)."),
    ("AVATAR_MAX_BYTES", "4194304",   "Tamanho máximo do upload em bytes (4 MB)."),
    ("AVATAR_SIZE_PX",   "512",       "Tamanho máximo em pixels após redimensionamento (quadrado)."),
])

tabela_env("4.6 E-mail (Gmail)", [
    ("EMAIL_HOST",     "smtp.gmail.com",        "Servidor SMTP. Para outro provedor, ajuste EMAIL_PORT também."),
    ("EMAIL_PORT",     "587",                   "Porta SMTP com STARTTLS. Gmail usa 587. SSL direto: 465."),
    ("EMAIL_USER",     "academia@gmail.com",    "Conta Gmail que envia os e-mails."),
    ("EMAIL_PASSWORD", "xxxx xxxx xxxx xxxx",   "⚠ Senha de app (16 chars). Não é a senha normal da conta."),
    ("EMAIL_FROM",     "academia@gmail.com",    "Endereço de remetente exibido no e-mail. Geralmente = EMAIL_USER."),
])
pb()

# ══════════════════════════════════════════════════════════════════════════════
# 5. O QUE MUDA DO DEV PARA PRODUÇÃO
# ══════════════════════════════════════════════════════════════════════════════
p("5. O que Muda do Desenvolvimento para Produção", "H1")
hr()

p("5.1 Backend (.env)", "H2")
mudancas_back = [
    ("RATELIMIT_STORAGE_URI",
     "<font face='Courier'>memory://</font> → <b>Redis automático</b>",
     "Configurado automaticamente pelo docker-compose como "
     "<font face='Courier'>redis://redis:6379/0</font>. Não precisa de alteração no .env."),
    ("ALLOWED_ORIGINS",
     "localhost:3000 → <b>URL de produção</b>",
     "Flask aceita requisições CORS apenas de <font face='Courier'>FRONTEND_URL</font>. "
     "Em produção, como frontend e backend ficam no mesmo domínio (nginx roteia), "
     "o browser não envia preflight CORS, mas a configuração é necessária para casos de "
     "acesso direto ao backend."),
    ("WEB_CONCURRENCY",
     "1 (dev) → <b>2+ (produção)</b>",
     "Múltiplos workers gunicorn. O APScheduler usa "
     "<font face='Courier'>preload_app=True</font> para rodar apenas no master "
     "e evitar e-mails duplicados."),
    ("Flask debug",
     "<b>DESLIGADO</b> (padrão)",
     "Em produção, <font face='Courier'>app.debug=False</font>. Erros 500 retornam "
     "mensagem genérica sem stack trace."),
]
tbl_back = Table(
    [[Paragraph("Variável", "CelB"), Paragraph("Dev → Produção", "CelB"), Paragraph("Impacto", "CelB")]] + [
        [Paragraph(v, styles["CelM"]), Paragraph(m, styles["Cel"]), Paragraph(d, styles["Cel"])]
        for v, m, d in mudancas_back
    ],
    colWidths=[3.8*cm, 3.8*cm, 7.4*cm], repeatRows=1
)
tbl_back.setStyle(TableStyle([
    ("BACKGROUND",    (0,0),  (-1,0), AZUL),
    ("GRID",          (0,0),  (-1,-1), 0.4, colors.HexColor("#cbd5e0")),
    ("ROWBACKGROUNDS",(0,1),  (-1,-1), [colors.white, CINZAC]),
    ("VALIGN",        (0,0),  (-1,-1), "TOP"),
    ("TOPPADDING",    (0,0),  (-1,-1), 4),
    ("BOTTOMPADDING", (0,0),  (-1,-1), 4),
    ("LEFTPADDING",   (0,0),  (-1,-1), 5),
]))
el.append(tbl_back)
sp(8)

p("5.2 Frontend (.env.local / Build Args)", "H2")
mudancas_front = [
    ("NEXT_PUBLIC_API_URL",
     "<font face='Courier'>http://127.0.0.1:5000</font> → <font face='Courier'>https://seudominio.com/api</font>",
     "Em produção, o nginx roteia <font face='Courier'>/api/</font> para Flask. "
     "A variável é embutida no JS no momento do build (não é possível mudar sem rebuildar)."),
    ("NEXT_PUBLIC_SUPABASE_URL",
     "Mesma URL do Supabase",
     "Igual ao dev — o Supabase é gerenciado externamente."),
    ("output: standalone",
     "Adicionado ao next.config.mjs",
     "Gera um bundle Node.js mínimo sem node_modules completo, "
     "reduzindo a imagem Docker em ~70%."),
    ("CSP nonce (proxy.js)",
     "<b>REPORT_ONLY = false</b>",
     "CSP em modo bloqueio — scripts sem nonce são bloqueados pelo browser. "
     "Mitigação central de XSS e roubo de token."),
]
tbl_front = Table(
    [[Paragraph("Item", "CelB"), Paragraph("Dev → Produção", "CelB"), Paragraph("Impacto", "CelB")]] + [
        [Paragraph(v, styles["CelM"]), Paragraph(m, styles["Cel"]), Paragraph(d, styles["Cel"])]
        for v, m, d in mudancas_front
    ],
    colWidths=[3.2*cm, 4.4*cm, 7.4*cm], repeatRows=1
)
tbl_front.setStyle(TableStyle([
    ("BACKGROUND",    (0,0),  (-1,0), AZUL),
    ("GRID",          (0,0),  (-1,-1), 0.4, colors.HexColor("#cbd5e0")),
    ("ROWBACKGROUNDS",(0,1),  (-1,-1), [colors.white, CINZAC]),
    ("VALIGN",        (0,0),  (-1,-1), "TOP"),
    ("TOPPADDING",    (0,0),  (-1,-1), 4),
    ("BOTTOMPADDING", (0,0),  (-1,-1), 4),
    ("LEFTPADDING",   (0,0),  (-1,-1), 5),
]))
el.append(tbl_front)
pb()

# ══════════════════════════════════════════════════════════════════════════════
# 6. CHECKLIST PÓS-DEPLOY
# ══════════════════════════════════════════════════════════════════════════════
p("6. Checklist Pós-Deploy", "H1")
hr()
checks = [
    ("[ ]", "Todos os containers com status healthy: <font face='Courier'>docker compose ps</font>"),
    ("[ ]", "<font face='Courier'>curl https://seudominio.com/api/health</font> retorna <font face='Courier'>{\"status\": \"ok\"}</font>"),
    ("[ ]", "Login funciona via interface web (testado em navegador privado)"),
    ("[ ]", "Criação de aluno com foto (webcam ou upload) funciona"),
    ("[ ]", "Relatório PDF é gerado e baixado corretamente"),
    ("[ ]", "Notificação de e-mail funciona (configure um aluno com vencimento próximo e aguarde)"),
    ("[ ]", "Cloudflare: painel mostra tráfego passando (Analytics → Overview)"),
    ("[ ]", "HTTPS funcionando: <font face='Courier'>https://</font> no URL, sem aviso de cert no browser"),
    ("[ ]", "CSP ativa: F12 → Console deve estar limpo (sem 'Content Security Policy' errors)"),
    ("[ ]", "<font face='Courier'>.env</font> NÃO está no repositório git: <font face='Courier'>git status | grep .env</font> não mostra o arquivo"),
    ("[ ]", "Backup automático do banco configurado no painel Supabase (Point-in-Time Recovery)"),
]
for check, desc in checks:
    row = Table([[Paragraph(check, styles["Mono"]), Paragraph(desc, styles["CorpoP"])]], colWidths=[0.8*cm, 14.2*cm])
    row.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    el.append(row)
sp(12)

# ══════════════════════════════════════════════════════════════════════════════
# 7. COMANDOS DE MANUTENÇÃO
# ══════════════════════════════════════════════════════════════════════════════
p("7. Comandos de Manutenção", "H1")
hr()

p("Atualizar a aplicação (novo código no repositório):", "H2")
cmd("cd /opt/academia\ngit pull origin main\ndocker compose up -d --build")
p("O build reutiliza as camadas em cache — só rebuilda o que mudou.", "CorpoP")
sp(6)

p("Ver logs em tempo real:", "H2")
cmd("docker compose logs -f backend    # logs do Flask\ndocker compose logs -f frontend   # logs do Next.js\ndocker compose logs -f nginx       # logs de acesso HTTP")
sp(6)

p("Reiniciar um serviço específico:", "H2")
cmd("docker compose restart backend\ndocker compose restart frontend")
sp(6)

p("Parar tudo (sem perder dados do Redis/volumes):", "H2")
cmd("docker compose down")
sp(6)

p("Limpar imagens antigas (liberar espaço após vários builds):", "H2")
cmd("docker image prune -f\ndocker system prune -f  # cuidado: remove também containers parados")
sp(6)

p("Ver uso de recursos (CPU, memória):", "H2")
cmd("docker stats")
sp(6)

p("Backup manual do Redis (dump.rdb):", "H2")
cmd("docker compose exec redis redis-cli BGSAVE\n# O arquivo fica no volume redis_data\n# Para localizar: docker volume inspect gestao-academia_redis_data")

# ── Rodapé ────────────────────────────────────────────────────────────────────
def rodape(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(CINZA)
    canvas.drawString(2*cm, 1.1*cm, "Guia de Deploy — Gestão de Academias · Confidencial")
    canvas.drawRightString(19*cm, 1.1*cm, f"Página {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#cbd5e0"))
    canvas.line(2*cm, 1.4*cm, 19*cm, 1.4*cm)
    canvas.restoreState()

doc = SimpleDocTemplate(
    SAIDA, pagesize=A4,
    leftMargin=2*cm, rightMargin=2*cm, topMargin=1.8*cm, bottomMargin=1.8*cm,
    title="Guia de Deploy — Gestão de Academias",
    author="Infraestrutura",
)
doc.build(el, onFirstPage=lambda c, d: None, onLaterPages=rodape)
print(f"PDF gerado em: {SAIDA}")
