# -*- coding: utf-8 -*-
"""Gera o relatório de troubleshooting (PDF) do deploy na VPS — da falha de
build até a aplicação no ar em https://academia.revizzicar.com.br.

Documenta, em formato pós-morte, os 5 problemas enfrentados na primeira subida
do stack Docker na VPS Hostinger (com CloudPanel + Cloudflare) e o passo a passo
para colocar o sistema no ar. Cada problema traz:
  - Sintoma (log/erro real observado)
  - Causa raiz
  - Correção aplicada (no arquivo versionado)
  - Por que funciona

Segue o mesmo estilo visual do scripts/gerar_doc_deploy.py.

Execute:
    cd backend
    python scripts/gerar_doc_troubleshooting.py
    # gera RELATORIO_TROUBLESHOOTING_DEPLOY.pdf na raiz do projeto
"""
import os
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether,
)

_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SAIDA = os.path.join(_RAIZ, "RELATORIO_TROUBLESHOOTING_DEPLOY.pdf")

# ── Paleta de cores ───────────────────────────────────────────────────────────
AZUL   = colors.HexColor("#1e3a5f")
AZUL2  = colors.HexColor("#2c5282")
CINZA  = colors.HexColor("#4a5568")
CINZAC = colors.HexColor("#edf2f7")
VERDE  = colors.HexColor("#276749")
VERDE_L= colors.HexColor("#f0fff4")
AMAR_L = colors.HexColor("#fffff0")
VERM   = colors.HexColor("#9b2c2c")
VERM_L = colors.HexColor("#fff5f5")
MONO   = colors.HexColor("#2d3748")

# ── Estilos ───────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

def S(name, **kw):
    styles.add(ParagraphStyle(name, **kw))

S("Capa",     fontName="Helvetica-Bold", fontSize=23, leading=29, textColor=AZUL,  alignment=TA_CENTER)
S("CapaSub",  fontName="Helvetica",      fontSize=12, leading=18, textColor=CINZA, alignment=TA_CENTER)
S("H1",       fontName="Helvetica-Bold", fontSize=15, leading=20, textColor=AZUL,  spaceBefore=14, spaceAfter=6)
S("H2",       fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=AZUL2, spaceBefore=10, spaceAfter=4)
S("H3",       fontName="Helvetica-Bold", fontSize=10, leading=14, textColor=MONO,  spaceBefore=8, spaceAfter=3)
S("Corpo",    fontName="Helvetica",      fontSize=9.5, leading=14, textColor=MONO,  alignment=TA_JUSTIFY, spaceAfter=4)
S("CorpoP",   fontName="Helvetica",      fontSize=9,   leading=13, textColor=MONO)
S("Mono",     fontName="Courier",        fontSize=8.3, leading=12, textColor=MONO)
S("MonoErr",  fontName="Courier",        fontSize=8.3, leading=12, textColor=VERM)
S("Cel",      fontName="Helvetica",      fontSize=8,   leading=11, textColor=MONO)
S("CelB",     fontName="Helvetica-Bold", fontSize=8,   leading=11, textColor=colors.white)
S("CelM",     fontName="Courier",        fontSize=7.6, leading=10, textColor=MONO)
S("Rodape",   fontName="Helvetica",      fontSize=7.5, leading=10, textColor=CINZA, alignment=TA_CENTER)
S("Badge",    fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=colors.white, alignment=TA_CENTER)

_RealParagraph = Paragraph
def Paragraph(text, style=None, **kw):
    if isinstance(style, str):
        style = styles[style]
    return _RealParagraph(text, style, **kw)

el = []

def p(txt, st="Corpo"):  el.append(Paragraph(txt, styles[st]))
def sp(h=6):             el.append(Spacer(1, h))
def hr():                el.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e0"), spaceBefore=4, spaceAfter=6))
def pb():                el.append(PageBreak())

def _br(texto):
    """Converte quebras de linha reais em <br/> (Paragraph colapsa \\n)."""
    return texto.replace("\n", "<br/>")

def problema(num, titulo, cor=AZUL):
    """Cabeçalho de problema: badge 'Pn' colorido + título."""
    row = Table(
        [[Paragraph(f"P{num}", "Badge"), Paragraph(f" {titulo}", "H1")]],
        colWidths=[1.2*cm, 13.8*cm]
    )
    row.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (0,0), cor),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",   (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0), (-1,-1), 6),
        ("LEFTPADDING",  (1,0), (1,0), 8),
    ]))
    el.append(KeepTogether([Spacer(1, 6), row]))
    sp(2)

def _box(texto, style_name, bg, linha):
    tbl = Table([[Paragraph(_br(texto), styles[style_name])]], colWidths=[15*cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), bg),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
        ("RIGHTPADDING", (0,0), (-1,-1), 8),
        ("TOPPADDING",   (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0), (-1,-1), 5),
        ("LINEBELOW",    (0,0), (-1,-1), 0.3, linha),
    ]))
    el.append(tbl)
    sp(3)

def cmd(texto):
    """Bloco de comando no terminal (fundo cinza, fonte mono)."""
    _box(texto, "Mono", CINZAC, colors.HexColor("#a0aec0"))

def log(texto):
    """Bloco de log/erro observado (fundo vermelho claro, fonte mono vermelha)."""
    _box(texto, "MonoErr", VERM_L, colors.HexColor("#feb2b2"))

def callout(simbolo, texto, bg, linha):
    tbl = Table(
        [[Paragraph(simbolo, styles["H2"]), Paragraph(texto, styles["Corpo"])]],
        colWidths=[0.7*cm, 14.3*cm]
    )
    tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), bg),
        ("LEFTPADDING",  (0,0), (-1,-1), 6),
        ("TOPPADDING",   (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ("VALIGN",       (0,0), (-1,-1), "TOP"),
        ("LINEBELOW",    (0,0), (-1,-1), 0.3, linha),
    ]))
    el.append(tbl)
    sp(4)

def nota(texto):  callout("⚠", texto, AMAR_L, colors.HexColor("#d69e2e"))
def dica(texto):  callout("✓", texto, VERDE_L, colors.HexColor("#9ae6b4"))

# ══════════════════════════════════════════════════════════════════════════════
# CAPA
# ══════════════════════════════════════════════════════════════════════════════
sp(100)
p("Relatório de Troubleshooting do Deploy", "Capa")
sp(4)
p("Sistema de Gestão de Academias", "CapaSub")
p("Da falha de build à aplicação no ar — VPS Hostinger + CloudPanel + Cloudflare", "CapaSub")
sp(30)
meta = Table([
    ["Aplicação",      "Flask (API) + Next.js (Frontend) + Redis + Nginx — todos Alpine"],
    ["Infraestrutura", "VPS Hostinger + Docker Compose (deploy via git push / git pull)"],
    ["Borda",          "Cloudflare (DNS/TLS) → CloudPanel (proxy host) → 127.0.0.1:8000"],
    ["Domínio",        "academia.revizzicar.com.br"],
    ["Banco",          "Supabase gerenciado (fora do Compose)"],
    ["Resultado",      "Aplicação no ar e validada de ponta a ponta"],
    ["Data",           date.today().strftime("%d/%m/%Y")],
    ["Versão",         "1.0 — gerado por scripts/gerar_doc_troubleshooting.py"],
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
# 1. CONTEXTO
# ══════════════════════════════════════════════════════════════════════════════
p("1. Contexto", "H1")
hr()
p("Primeira subida do stack Docker em produção na VPS. O fluxo de trabalho adotado: "
  "o código é versionado e enviado com <font face='Courier'>git push</font> a partir da "
  "máquina local (Windows); na VPS, em <font face='Courier'>/opt/academia</font>, faz-se "
  "<font face='Courier'>git pull</font> seguido de "
  "<font face='Courier'>docker compose up -d --build</font>.", "Corpo")
sp(2)
p("Dois pontos importantes desse fluxo:", "CorpoP")
for item in [
    "O <font face='Courier'>.env</font> é editado <b>manualmente na VPS</b> (está no .gitignore, "
    "nunca trafega pelo git) — segredos do Supabase, e-mail e <font face='Courier'>FRONTEND_URL</font>.",
    "As imagens são <b>Alpine Linux</b> (musl libc), enquanto o desenvolvimento local é no "
    "Windows. Vários problemas vieram justamente dessa diferença de plataforma.",
]:
    el.append(Paragraph(f"• {item}", styles["CorpoP"])); sp(2)
sp(4)
p("Arquitetura da borda (como o mundo externo chega ao stack):", "H2")
cmd("Cloudflare  (DNS / TLS / \"Allow traffic from Cloudflare only\")\n"
    "   -> CloudPanel  (proxy reverso do host, termina o TLS)\n"
    "      -> http://127.0.0.1:8000\n"
    "         -> nginx do compose  ->  / = frontend:3000\n"
    "                               -> /api/ = backend:5000")
nota("O Supabase é gerenciado externamente (não entra no Compose). O Redis é interno e "
     "serve ao rate limiting compartilhado e ao lock do APScheduler.")
sp(4)

# Tabela resumo
p("Resumo dos 5 problemas", "H2")
resumo = Table(
    [[Paragraph("#", "CelB"), Paragraph("Sintoma", "CelB"), Paragraph("Camada", "CelB"),
      Paragraph("Causa raiz", "CelB"), Paragraph("Correção", "CelB")]] + [
        [Paragraph("P1", styles["CelM"]),
         Paragraph("Build do frontend aborta no <font face='Courier'>npm run build</font>", styles["Cel"]),
         Paragraph("Frontend", styles["Cel"]),
         Paragraph("Lock gerado no Windows não traz o binário nativo musl", styles["Cel"]),
         Paragraph("rm do lock + npm install no builder", styles["Cel"])],
        [Paragraph("P2", styles["CelM"]),
         Paragraph("Backend em loop <font face='Courier'>Restarting (1)</font>", styles["Cel"]),
         Paragraph("Backend", styles["Cel"]),
         Paragraph("Deps em /root/.local, ilegível pelo usuário appuser", styles["Cel"]),
         Paragraph("Deps em /home/appuser/.local + HOME", styles["Cel"])],
        [Paragraph("P3", styles["CelM"]),
         Paragraph("Container <font face='Courier'>Up (unhealthy)</font>", styles["Cel"]),
         Paragraph("Backend / Frontend", styles["Cel"]),
         Paragraph("Healthcheck em 'localhost' cai em IPv6 (::1)", styles["Cel"]),
         Paragraph("Sonda usa 127.0.0.1", styles["Cel"])],
        [Paragraph("P4", styles["CelM"]),
         Paragraph("CloudPanel não alcança o stack / conflito de porta", styles["Cel"]),
         Paragraph("Borda", styles["Cel"]),
         Paragraph("nginx publicado em 80:80, mas CloudPanel aponta para 8000", styles["Cel"]),
         Paragraph("nginx em 127.0.0.1:8000:80", styles["Cel"])],
        [Paragraph("P5", styles["CelM"]),
         Paragraph("Scripts bloqueados pela CSP; tela \"morta\"", styles["Cel"]),
         Paragraph("Frontend", styles["Cel"]),
         Paragraph("Nonce por-request + página pré-renderizada (nonces não casam)", styles["Cel"]),
         Paragraph("Força render dinâmico (await connection)", styles["Cel"])],
    ],
    colWidths=[0.8*cm, 4.0*cm, 2.3*cm, 4.2*cm, 3.7*cm], repeatRows=1
)
resumo.setStyle(TableStyle([
    ("BACKGROUND",    (0,0),  (-1,0), AZUL),
    ("GRID",          (0,0),  (-1,-1), 0.4, colors.HexColor("#cbd5e0")),
    ("ROWBACKGROUNDS",(0,1),  (-1,-1), [colors.white, CINZAC]),
    ("VALIGN",        (0,0),  (-1,-1), "TOP"),
    ("TOPPADDING",    (0,0),  (-1,-1), 4),
    ("BOTTOMPADDING", (0,0),  (-1,-1), 4),
    ("LEFTPADDING",   (0,0),  (-1,-1), 4),
]))
el.append(resumo)
pb()

# ══════════════════════════════════════════════════════════════════════════════
# 2. OS PROBLEMAS E CORREÇÕES
# ══════════════════════════════════════════════════════════════════════════════
p("2. Os Problemas e Correções", "H1")
hr()
p("Cada problema segue o mesmo formato: sintoma observado, causa raiz, correção (no "
  "arquivo versionado) e por que funciona. Os quatro primeiros foram bloqueadores de "
  "infraestrutura; o quinto é da camada de aplicação — a CSP só se manifesta com o app "
  "já no ar.", "Corpo")

# ──────────────────────────────────────────────────────────────────────────────
# P1
# ──────────────────────────────────────────────────────────────────────────────
problema(1, "Build do frontend falha: binário musl do lightningcss ausente", VERM)

p("Sintoma", "H3")
p("Durante <font face='Courier'>docker compose up -d --build</font>, o passo "
  "<font face='Courier'>RUN npm run build</font> do frontend aborta:", "CorpoP")
log("Error: Cannot find module '../lightningcss.linux-x64-musl.node'\n"
    "Require stack:\n"
    " - /app/node_modules/lightningcss/node/index.js\n"
    " - /app/node_modules/@tailwindcss/node/dist/index.js\n"
    " - /app/node_modules/@tailwindcss/postcss/dist/index.js")

p("Causa raiz", "H3")
p("O Tailwind v4 usa o <font face='Courier'>lightningcss</font>, que tem binários nativos "
  "<b>por plataforma</b> (cada SO/arquitetura tem o seu <font face='Courier'>.node</font>). "
  "O <font face='Courier'>package-lock.json</font> foi gerado no Windows e, por uma "
  "particularidade do npm, só grava a entrada instalável completa "
  "(com <font face='Courier'>resolved</font>/<font face='Courier'>integrity</font>) do binário "
  "<b>da plataforma onde o lock foi criado</b> — o <font face='Courier'>win32-x64-msvc</font>. "
  "Os demais (incluindo <font face='Courier'>linux-x64-musl</font>, exigido pelo Alpine) ficam "
  "apenas listados, sem entrada instalável. Resultado: na VPS, o "
  "<font face='Courier'>npm install</font> lê o lock, não encontra como instalar o binário musl "
  "e o <b>pula</b> — o <font face='Courier'>.node</font> nunca é baixado.", "Corpo")

p("Correção", "H3")
p("No <font face='Courier'>frontend/Dockerfile</font>, remover o lock dentro do builder "
  "força o npm a re-resolver os binários nativos para a plataforma do container (Alpine/musl), "
  "consultando o registry na hora:", "CorpoP")
cmd("# frontend/Dockerfile (estágio builder)\n"
    "COPY package.json package-lock.json ./\n"
    "RUN rm -f package-lock.json && npm install")

p("Por que funciona", "H3")
p("Sem o lock 'envenenado' pelo Windows, o npm resolve as "
  "<font face='Courier'>optionalDependencies</font> nativas (lightningcss e "
  "<font face='Courier'>@tailwindcss/oxide</font>) de acordo com a plataforma real do build. "
  "O lock do Windows continua versionado para o desenvolvimento local — mantendo a "
  "compatibilidade Windows local &harr; Alpine na VPS.", "Corpo")
dica("Alternativas descartadas: (a) gerar o lock no Linux e versioná-lo quebraria o "
     "<font face='Courier'>npm ci</font> no Windows; (b) instalar o binário musl explicitamente "
     "fixaria a arquitetura (quebraria em arm64). Remover o lock no builder é o mais robusto.")
pb()

# ══════════════════════════════════════════════════════════════════════════════
# P2
# ══════════════════════════════════════════════════════════════════════════════
problema(2, "Backend em loop de restart: 'No module named gunicorn'", VERM)

p("Sintoma", "H3")
p("O container do backend sobe e cai imediatamente, ficando em "
  "<font face='Courier'>Restarting (1)</font>. Nos logs:", "CorpoP")
log("backend-1  | /usr/local/bin/python: No module named gunicorn\n"
    "backend-1  | /usr/local/bin/python: No module named gunicorn\n"
    "backend-1  | ... (repete a cada reinício)")
p("Pista de diagnóstico: o backend só começa a subir <b>depois</b> do Redis ficar healthy "
  "(<font face='Courier'>depends_on</font>), e falhava ~0,3s após isso — ou seja, "
  "<b>crash imediato no boot</b>, não healthcheck lento.", "CorpoP")

p("Causa raiz", "H3")
p("O <font face='Courier'>backend/Dockerfile</font> instala as dependências com "
  "<font face='Courier'>pip install --user</font>, que as coloca em "
  "<font face='Courier'>/root/.local</font>. Mas o container roda como "
  "<font face='Courier'>USER appuser</font> (sem privilégios, por segurança). No Alpine, "
  "<font face='Courier'>/root</font> tem permissão <font face='Courier'>0700</font> — só o root "
  "entra. O <font face='Courier'>appuser</font> não consegue atravessar "
  "<font face='Courier'>/root</font> para importar os pacotes, então o Python não acha o "
  "gunicorn e o processo morre na hora.", "Corpo")

p("Correção", "H3")
p("Copiar as dependências para a HOME do próprio <font face='Courier'>appuser</font> "
  "(com <font face='Courier'>--chown</font>) e definir <font face='Courier'>HOME</font> "
  "explicitamente:", "CorpoP")
cmd("# backend/Dockerfile (estágio runtime)\n"
    "RUN adduser -D appuser\n"
    "COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local\n"
    "COPY --chown=appuser:appuser app/ ./app/\n"
    "COPY --chown=appuser:appuser run.py gunicorn.conf.py ./\n"
    "ENV HOME=/home/appuser \\\n"
    "    PATH=/home/appuser/.local/bin:$PATH")

p("Por que funciona", "H3")
p("Em <font face='Courier'>/home/appuser/.local</font>, os pacotes pertencem ao usuário que "
  "roda o processo e ficam legíveis. O detalhe crítico é o "
  "<font face='Courier'>ENV HOME=/home/appuser</font>: a instrução "
  "<font face='Courier'>USER</font> do Docker <b>não</b> define a variável "
  "<font face='Courier'>$HOME</font>, e é dela que o Python deriva o caminho do "
  "<i>user-site</i> (<font face='Courier'>~/.local/lib/...</font>). Sem o "
  "<font face='Courier'>HOME</font> correto, o Python voltaria a procurar em "
  "<font face='Courier'>/root/.local</font>.", "Corpo")
pb()

# ══════════════════════════════════════════════════════════════════════════════
# P3
# ══════════════════════════════════════════════════════════════════════════════
problema(3, "Container 'unhealthy': healthcheck em localhost cai em IPv6", VERM)

p("Sintoma", "H3")
p("O gunicorn agora <b>sobe e fica de pé</b> (workers ativos), mas o container permanece "
  "<font face='Courier'>Up (unhealthy)</font> e o nginx, que depende dele, nunca inicia. "
  "Nos logs do gunicorn não aparece nenhuma linha de acesso ao <font face='Courier'>/health</font> "
  "— sinal de que a sonda <b>não chega</b> ao app:", "CorpoP")
log("[INFO] Starting gunicorn 23.0.0\n"
    "[INFO] Listening at: http://0.0.0.0:5000 (1)\n"
    "[INFO] Booting worker with pid: 8\n"
    "(nenhum log de requisição GET /health depois disso)")

p("Diagnóstico", "H3")
p("Testando dentro do container, isolando IPv4 de IPv6:", "CorpoP")
cmd("$ wget -qO- http://127.0.0.1:5000/health   ->  {\"status\":\"ok\"}   (EXIT=0)\n"
    "$ wget -qO- http://localhost:5000/health    ->  can't connect: Connection refused (EXIT=1)")

p("Causa raiz", "H3")
p("O healthcheck (definido no <font face='Courier'>docker-compose.yml</font>) usava "
  "<font face='Courier'>http://localhost:5000/health</font>. Dentro do container, "
  "<font face='Courier'>localhost</font> resolve primeiro para <b>IPv6 "
  "<font face='Courier'>::1</font></b>, mas o gunicorn (e o Next.js) escutam apenas em "
  "<b>IPv4</b> (<font face='Courier'>0.0.0.0</font>). A sonda batia em "
  "<font face='Courier'>::1</font>, levava <i>Connection refused</i> e nunca tocava o app — "
  "marcando o container como unhealthy.", "Corpo")

p("Correção", "H3")
p("Trocar <font face='Courier'>localhost</font> por <font face='Courier'>127.0.0.1</font> nos "
  "healthchecks do backend e do frontend:", "CorpoP")
cmd("# docker-compose.yml\n"
    "# backend:\n"
    "test: [\"CMD-SHELL\", \"wget -qO- http://127.0.0.1:5000/health | grep -q ok\"]\n"
    "# frontend:\n"
    "test: [\"CMD-SHELL\", \"wget -qO- http://127.0.0.1:3000/ | grep -q html\"]")

p("Por que funciona", "H3")
p("<font face='Courier'>127.0.0.1</font> é endereço IPv4 explícito, exatamente onde os "
  "servidores escutam. Sem ambiguidade de resolução de nome, a sonda conecta, recebe o "
  "<font face='Courier'>{\"status\":\"ok\"}</font> e o container passa a "
  "<font face='Courier'>healthy</font>.", "Corpo")
nota("Esse é um dos enganadores mais comuns em healthchecks de container: o app está "
     "perfeitamente saudável, mas a sonda mira o protocolo errado. Sempre prefira "
     "<font face='Courier'>127.0.0.1</font> a <font face='Courier'>localhost</font> em "
     "healthchecks quando o servidor faz bind em IPv4.")
pb()

# ══════════════════════════════════════════════════════════════════════════════
# P4
# ══════════════════════════════════════════════════════════════════════════════
problema(4, "Encaixe com o CloudPanel: porta de publicação do nginx", VERM)

p("Sintoma / contexto", "H3")
p("Com os 3 containers <font face='Courier'>healthy</font>, faltava a borda. No host, o "
  "<b>CloudPanel</b> (proxy reverso da Hostinger) foi configurado para encaminhar o domínio "
  "para <font face='Courier'>http://127.0.0.1:8000</font>. Mas o nginx do compose publicava em "
  "<font face='Courier'>80:80</font> — então nada respondia na porta 8000, e ainda havia "
  "conflito com a porta 80/443 que o CloudPanel já ocupa no host.", "Corpo")

p("Correção", "H3")
p("Publicar o nginx do compose em <font face='Courier'>127.0.0.1:8000</font> — exatamente onde "
  "o CloudPanel aponta:", "CorpoP")
cmd("# docker-compose.yml (serviço nginx)\n"
    "ports:\n"
    "  - \"127.0.0.1:8000:80\"")

p("Por que funciona", "H3")
for item in [
    "<b>Casa com o CloudPanel</b>: o alvo <font face='Courier'>127.0.0.1:8000</font> agora "
    "responde (o nginx interno, que separa <font face='Courier'>/</font> &rarr; frontend e "
    "<font face='Courier'>/api/</font> &rarr; backend).",
    "<b>Sem conflito de porta</b>: o stack não disputa mais a 80/443 com o CloudPanel.",
    "<b>Bind em 127.0.0.1 (não 0.0.0.0)</b>: o stack só é alcançável pelo próprio host "
    "(pelo CloudPanel), nunca direto da internet — defesa em profundidade.",
]:
    el.append(Paragraph(f"• {item}", styles["CorpoP"])); sp(2)
sp(4)
nota("Mantemos o nginx do compose mesmo com o CloudPanel na frente: é ele que faz o "
     "roteamento <font face='Courier'>/api/</font> &rarr; Flask e remove o prefixo "
     "<font face='Courier'>/api/</font> antes de repassar. Assim o CloudPanel precisa de um "
     "único alvo, em vez de expor frontend e backend separadamente.")
pb()

# ══════════════════════════════════════════════════════════════════════════════
# P5
# ══════════════════════════════════════════════════════════════════════════════
problema(5, "Frontend \"morto\": a CSP bloqueia todos os scripts", VERM)

p("Sintoma", "H3")
p("Com o app no ar, a tela carregava sem interatividade e o console do navegador "
  "despejava dezenas de violações de CSP:", "CorpoP")
log("Refused to load the script '<URL>': violates Content Security Policy directive\n"
    "\"script-src 'self' 'nonce-...' 'strict-dynamic'\".\n"
    "Executing inline script violates ... a nonce ('nonce-...') is required to enable\n"
    "inline execution. The action has been blocked.")

p("Causa raiz", "H3")
p("O <font face='Courier'>proxy.js</font> (o \"proxy\" do Next 16, antigo middleware) gera um "
  "nonce <b>novo a cada requisição</b> e o coloca no header CSP. O Next injeta esse nonce nos "
  "&lt;script&gt; <b>apenas durante o SSR</b>. Mas as páginas estavam sendo "
  "<b>pré-renderizadas no build</b> (no <font face='Courier'>curl</font>: "
  "<font face='Courier'>x-nextjs-prerender: 1</font> e <font face='Courier'>cache HIT</font>): "
  "o shell HTML cacheado carregava scripts com nonce ausente/velho, enquanto o header trazia um "
  "nonce diferente a cada request. O navegador compara, não casa, e bloqueia tudo — e o "
  "<font face='Courier'>strict-dynamic</font> derruba o restante em cascata.", "Corpo")
nota("Confirmado na doc oficial do Next 16: \"To use a nonce, your page must be dynamically "
     "rendered. Static pages are generated at build time, when no request or response headers "
     "exist — so no nonce can be injected.\"")

p("Correção", "H3")
p("Forçar renderização dinâmica no <font face='Courier'>app/layout.js</font> (que envolve todas "
  "as rotas) com <font face='Courier'>await connection()</font> — o método endossado pela doc do "
  "Next 16 para este caso. O antigo <font face='Courier'>export const dynamic</font> mudou de "
  "comportamento nesta versão (removido com Cache Components), por isso não foi usado.", "CorpoP")
cmd("// frontend/app/layout.js\n"
    "import { connection } from \"next/server\";\n"
    "\n"
    "export default async function RootLayout({ children }) {\n"
    "  await connection();   // opta toda a árvore por render dinâmico\n"
    "  return ( /* <html> ... */ );\n"
    "}")

p("Por que funciona", "H3")
p("Com render dinâmico, o Next gera o HTML por requisição e injeta o nonce nos scripts no mesmo "
  "ciclo em que o header CSP é criado — então os nonces sempre casam. O "
  "<font face='Courier'>next build</font> confirmou: todas as rotas passaram de estáticas para "
  "<font face='Courier'>ƒ (Dynamic)</font>, e o <font face='Courier'>cache-control</font> da "
  "resposta virou <font face='Courier'>no-store</font>.", "Corpo")
dica("Trade-off aceito: o shell HTML deixa de ser cacheado estaticamente (renderiza por request). "
     "Neste portal atrás de login, com dados buscados no client, o custo é mínimo — e o JS pesado "
     "(<font face='Courier'>_next/static/*</font>) continua cacheado normalmente.")
pb()

# ══════════════════════════════════════════════════════════════════════════════
# 3. COMO COLOCAR O SISTEMA NO AR
# ══════════════════════════════════════════════════════════════════════════════
p("3. Como Colocar o Sistema no Ar (passo a passo)", "H1")
hr()
p("Resumo reproduzível para subir (ou ressubir) o sistema nesta infraestrutura: VPS com "
  "CloudPanel como proxy reverso do host e Cloudflare na borda. O fluxo de trabalho é "
  "<font face='Courier'>git push</font> (local) &rarr; <font face='Courier'>git pull</font> na "
  "VPS &rarr; <font face='Courier'>docker compose up -d --build</font>.", "Corpo")
sp(4)

p("3.1 Pré-requisitos na VPS", "H3")
for item in [
    "Docker Engine + Docker Compose v2 (<font face='Courier'>docker compose version</font>).",
    "Git, e o repositório clonado em <font face='Courier'>/opt/academia</font>.",
    "CloudPanel instalado (gerencia o domínio e o TLS no host).",
    "Projeto Supabase criado, com as migrations 001–011 rodadas no SQL Editor e o bucket "
    "<font face='Courier'>avatars</font> público.",
]:
    el.append(Paragraph(f"• {item}", styles["CorpoP"])); sp(2)
sp(3)

p("3.2 Atualizar o código na VPS", "H3")
cmd("cd /opt/academia\ngit pull")

p("3.3 Configurar o .env (manual na VPS — nunca via git)", "H3")
p("O <font face='Courier'>.env</font> está no <font face='Courier'>.gitignore</font>; ele é criado "
  "e editado direto na VPS. Mínimos obrigatórios:", "CorpoP")
cmd("cp .env.production.example .env   # só na primeira vez\nnano .env")
for item in [
    "<font face='Courier'>FRONTEND_URL=https://academia.revizzicar.com.br</font> (sem barra final)",
    "<font face='Courier'>SUPABASE_URL</font>, <font face='Courier'>SUPABASE_ANON_KEY</font>, "
    "<font face='Courier'>SUPABASE_SERVICE_ROLE_KEY</font> (esta é secreta — bypassa RLS)",
    "<font face='Courier'>EMAIL_USER</font> / <font face='Courier'>EMAIL_PASSWORD</font> "
    "(senha de app do Gmail, 16 chars)",
]:
    el.append(Paragraph(f"• {item}", styles["CorpoP"])); sp(2)
sp(3)

p("3.4 Build e subir os containers", "H3")
cmd("docker compose up -d --build\ndocker compose ps        # todos devem ficar Up (healthy)")

p("3.5 CloudPanel — proxy reverso do host", "H3")
for item in [
    "Crie o site/proxy reverso apontando o domínio para "
    "<font face='Courier'>http://127.0.0.1:8000</font> (onde o nginx do compose publica).",
    "Ative \"Allow traffic from Cloudflare only\" para fechar o origin a acessos diretos.",
]:
    el.append(Paragraph(f"• {item}", styles["CorpoP"])); sp(2)
sp(3)

p("3.6 Cloudflare — DNS + TLS", "H3")
for item in [
    "Registro <b>A</b> de <font face='Courier'>academia</font> &rarr; IP da VPS, com proxy "
    "<b>Laranja (Proxied)</b>. Em \"DNS only\" (cinza), o CloudPanel bloquearia tudo.",
    "SSL/TLS em modo <b>Full</b> (com \"Cloudflare only\", Flexible causa loop de redirect).",
]:
    el.append(Paragraph(f"• {item}", styles["CorpoP"])); sp(2)
sp(3)

p("3.7 Validar (ver a seção 4)", "H3")
p("Teste em camadas: <font face='Courier'>127.0.0.1:8000</font> (Docker puro) &rarr; domínio "
  "(borda completa) &rarr; navegador (login + console limpo).", "CorpoP")
pb()

# ══════════════════════════════════════════════════════════════════════════════
# 4. VERIFICAÇÃO FINAL
# ══════════════════════════════════════════════════════════════════════════════
p("4. Verificação Final (de ponta a ponta)", "H1")
hr()
p("Com tudo corrigido, todos os serviços ficaram <font face='Courier'>healthy</font> e a "
  "aplicação respondeu nas três camadas. A verificação foi feita em camadas — as duas "
  "primeiras são locais (isolam o Docker), a terceira passa pela borda completa:", "Corpo")
sp(4)

p("Camada 1 — nginx do compose &rarr; backend (local, sem CloudPanel)", "H3")
cmd("$ curl http://127.0.0.1:8000/api/health\n{\"status\":\"ok\"}")

p("Camada 2 — nginx do compose &rarr; frontend (local)", "H3")
cmd("$ curl -I http://127.0.0.1:8000/\nHTTP/1.1 200 OK\nContent-Type: text/html; charset=utf-8")

p("Camada 3 — borda completa (Cloudflare &rarr; CloudPanel &rarr; Docker)", "H3")
cmd("$ curl https://academia.revizzicar.com.br/api/health\n{\"status\":\"ok\"}")

p("Camada 4 — frontend no navegador (CSP)", "H3")
p("Abrir o domínio em aba anônima, F12 &rarr; Console: sem violações de CSP, a página hidrata e "
  "o login funciona. O header da home deve trazer "
  "<font face='Courier'>cache-control: no-store</font> (render dinâmico ativo) e <b>não</b> "
  "trazer <font face='Courier'>x-nextjs-prerender</font>.", "CorpoP")

sp(4)
dica("Essa verificação em camadas é uma técnica de diagnóstico reutilizável: se a Camada 1 e 2 "
     "passam mas a 3 falha, o problema está <b>fora</b> do Docker (Cloudflare/CloudPanel) — "
     "evitando procurar no lugar errado.")
sp(6)

p("Estado final dos containers", "H2")
estado = Table(
    [[Paragraph("Container", "CelB"), Paragraph("Status", "CelB"), Paragraph("Porta", "CelB")]] + [
        [Paragraph(n, styles["CelM"]), Paragraph(s, styles["Cel"]), Paragraph(po, styles["CelM"])]
        for n, s, po in [
            ("academia-nginx-1",    "Up",            "127.0.0.1:8000->80"),
            ("academia-backend-1",  "Up (healthy)",  "5000 (interno)"),
            ("academia-frontend-1", "Up (healthy)",  "3000 (interno)"),
            ("academia-redis-1",    "Up (healthy)",  "6379 (interno)"),
        ]
    ],
    colWidths=[5.0*cm, 4.0*cm, 6.0*cm], repeatRows=1
)
estado.setStyle(TableStyle([
    ("BACKGROUND",    (0,0),  (-1,0), VERDE),
    ("GRID",          (0,0),  (-1,-1), 0.4, colors.HexColor("#cbd5e0")),
    ("ROWBACKGROUNDS",(0,1),  (-1,-1), [colors.white, VERDE_L]),
    ("VALIGN",        (0,0),  (-1,-1), "MIDDLE"),
    ("TOPPADDING",    (0,0),  (-1,-1), 4),
    ("BOTTOMPADDING", (0,0),  (-1,-1), 4),
    ("LEFTPADDING",   (0,0),  (-1,-1), 5),
]))
el.append(estado)
pb()

# ══════════════════════════════════════════════════════════════════════════════
# 5. PENDÊNCIAS E LIÇÕES
# ══════════════════════════════════════════════════════════════════════════════
p("5. Requisitos da Borda, Pendências e Lições", "H1")
hr()

p("5.1 Requisitos do Cloudflare + CloudPanel", "H2")
for item in [
    "<b>DNS proxied (nuvem laranja)</b>: como o CloudPanel está em "
    "\"Allow traffic from Cloudflare only\", o registro de "
    "<font face='Courier'>academia.revizzicar.com.br</font> precisa estar proxied. Em "
    "\"DNS only\" (cinza), o CloudPanel bloquearia todo o tráfego.",
    "<b>SSL mode Full (ou Full Strict)</b> no Cloudflare. Com \"Cloudflare only\" + Flexible "
    "ocorre loop de redirecionamento.",
]:
    el.append(Paragraph(f"• {item}", styles["CorpoP"])); sp(2)
sp(4)

p("5.2 Pendências (não bloqueiam o funcionamento)", "H2")
for item in [
    "<b>X-Forwarded-Proto</b>: o CloudPanel termina o HTTPS e fala HTTP com o nginx interno, "
    "então o Flask vê a requisição como não-segura e omite o header HSTS. É cosmético "
    "(o TLS real está no CloudPanel/Cloudflare); pode-se propagar o protocolo original depois.",
    "<b>Set de IPs do Cloudflare no nginx</b>: o <font face='Courier'>nginx.conf</font> usa "
    "<font face='Courier'>set_real_ip_from 0.0.0.0/0</font>; para endurecer, restringir aos CIDR "
    "do Cloudflare (o rate limiting por IP fica mais confiável).",
]:
    el.append(Paragraph(f"• {item}", styles["CorpoP"])); sp(2)
sp(2)
dica("O teste funcional no navegador (login + console sem violações de CSP) já foi validado — "
     "o ciclo de deploy está fechado e a aplicação operacional.")
sp(2)

p("5.3 Lições para os próximos deploys", "H2")
licoes = Table(
    [[Paragraph("Tema", "CelB"), Paragraph("Lição", "CelB")]] + [
        [Paragraph(t, styles["Cel"]), Paragraph(l, styles["Cel"])]
        for t, l in [
            ("Lockfiles nativos",
             "Dependências com binários nativos (lightningcss, oxide, etc.) + lock de outra "
             "plataforma = binário ausente. No build em container, re-resolver para a plataforma alvo."),
            ("Usuário sem root",
             "pip install --user põe deps em /root/.local; container que roda como não-root precisa "
             "delas na própria HOME, e o HOME precisa ser definido explicitamente (USER não o define)."),
            ("Healthchecks",
             "Prefira 127.0.0.1 a localhost quando o servidor faz bind em IPv4 — evita o falso "
             "'unhealthy' por resolução IPv6."),
            ("Diagnóstico em camadas",
             "Teste local (127.0.0.1:porta) antes da borda (domínio). Isola se o problema é "
             "do Docker ou do proxy/CDN."),
            ("Separar config de imagem",
             "Healthcheck e porta vivem no compose (não na imagem): corrigi-los exige só "
             "'docker compose up -d', sem rebuild."),
            ("CSP com nonce",
             "Nonce por-request exige renderização dinâmica. Em apps Next pré-renderizados, "
             "force o render dinâmico (await connection) ou o navegador bloqueia todos os scripts."),
        ]
    ],
    colWidths=[3.5*cm, 11.5*cm], repeatRows=1
)
licoes.setStyle(TableStyle([
    ("BACKGROUND",    (0,0),  (-1,0), AZUL),
    ("GRID",          (0,0),  (-1,-1), 0.4, colors.HexColor("#cbd5e0")),
    ("ROWBACKGROUNDS",(0,1),  (-1,-1), [colors.white, CINZAC]),
    ("VALIGN",        (0,0),  (-1,-1), "TOP"),
    ("TOPPADDING",    (0,0),  (-1,-1), 4),
    ("BOTTOMPADDING", (0,0),  (-1,-1), 4),
    ("LEFTPADDING",   (0,0),  (-1,-1), 5),
]))
el.append(licoes)
sp(10)
p("Resultado: do primeiro erro de build à aplicação no ar, cada falha apontou a próxima — "
  "build &rarr; boot &rarr; healthcheck &rarr; borda &rarr; CSP. A aplicação está operacional "
  "em https://academia.revizzicar.com.br.", "Corpo")

# ── Rodapé ────────────────────────────────────────────────────────────────────
def rodape(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(CINZA)
    canvas.drawString(2*cm, 1.1*cm, "Troubleshooting do Deploy — Gestão de Academias · Confidencial")
    canvas.drawRightString(19*cm, 1.1*cm, f"Página {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#cbd5e0"))
    canvas.line(2*cm, 1.4*cm, 19*cm, 1.4*cm)
    canvas.restoreState()

doc = SimpleDocTemplate(
    SAIDA, pagesize=A4,
    leftMargin=2*cm, rightMargin=2*cm, topMargin=1.8*cm, bottomMargin=1.8*cm,
    title="Relatório de Troubleshooting do Deploy — Gestão de Academias",
    author="Infraestrutura",
)
doc.build(el, onFirstPage=lambda c, d: None, onLaterPages=rodape)
print(f"PDF gerado em: {SAIDA}")
