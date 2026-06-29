# -*- coding: utf-8 -*-
"""Gera o relatório de segurança (PDF) da API Gestão de Academias.

Análise read-only — apenas leitura de código. Nenhuma alteração na aplicação.
"""
import os
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable,
)

# Saída na raiz do projeto (…/gestao-academia/RELATORIO_SEGURANCA.pdf),
# independentemente de onde o comando for executado.
_RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SAIDA = os.path.join(_RAIZ, "RELATORIO_SEGURANCA.pdf")

# ── Paleta ────────────────────────────────────────────────────────────────────
AZUL   = colors.HexColor("#1e3a5f")
AZUL2  = colors.HexColor("#2c5282")
CINZA  = colors.HexColor("#4a5568")
CINZAC = colors.HexColor("#edf2f7")
CRIT   = colors.HexColor("#c0392b")
ALTO   = colors.HexColor("#e67e22")
MED    = colors.HexColor("#d4a017")
BAIXO  = colors.HexColor("#2e7d32")
INFO   = colors.HexColor("#2c5282")
VERDE  = colors.HexColor("#2e7d32")

styles = getSampleStyleSheet()

def S(name, **kw):
    styles.add(ParagraphStyle(name, **kw))

S("Capa",      fontName="Helvetica-Bold", fontSize=26, leading=32, textColor=AZUL,  alignment=TA_CENTER)
S("CapaSub",   fontName="Helvetica",      fontSize=13, leading=18, textColor=CINZA, alignment=TA_CENTER)
S("H1",        fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=AZUL,  spaceBefore=14, spaceAfter=8)
S("H2",        fontName="Helvetica-Bold", fontSize=12.5, leading=16, textColor=AZUL2, spaceBefore=10, spaceAfter=5)
S("Corpo",     fontName="Helvetica",      fontSize=9.5, leading=14, textColor=colors.HexColor("#1a202c"), alignment=TA_LEFT, spaceAfter=5)
S("CorpoP",    fontName="Helvetica",      fontSize=9,  leading=13, textColor=colors.HexColor("#1a202c"))
S("Cel",       fontName="Helvetica",      fontSize=7.8, leading=10, textColor=colors.HexColor("#1a202c"))
S("CelB",      fontName="Helvetica-Bold", fontSize=7.8, leading=10, textColor=colors.white)
S("CelMono",   fontName="Courier",        fontSize=7.6, leading=10, textColor=colors.HexColor("#1a202c"))
S("Rodape",    fontName="Helvetica",      fontSize=7.5, leading=10, textColor=CINZA, alignment=TA_CENTER)
S("Badge",     fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=colors.white, alignment=TA_CENTER)

# Permite passar o nome do estilo (string) como 2º argumento do Paragraph.
_RealParagraph = Paragraph
def Paragraph(text, style=None, **kw):
    if isinstance(style, str):
        style = styles[style]
    return _RealParagraph(text, style, **kw)

el = []
def p(txt, st="Corpo"): el.append(Paragraph(txt, styles[st]))
def sp(h=6): el.append(Spacer(1, h))
def hr(): el.append(HRFlowable(width="100%", thickness=0.6, color=colors.HexColor("#cbd5e0"), spaceBefore=4, spaceAfter=8))

# ══════════════════════════════════════════════════════════════════════════════
# CAPA
# ══════════════════════════════════════════════════════════════════════════════
sp(120)
p("Relatório de Análise de Segurança", "Capa")
sp(6)
p("API Backend — Sistema de Gestão de Academias", "CapaSub")
p("Flask + Supabase (PostgreSQL) · React/Next.js", "CapaSub")
sp(40)
cap = Table([
    ["Escopo", "Endpoints da API + arquitetura de autenticação/autorização"],
    ["Tipo", "Análise estática (revisão de código)"],
    ["Revisão", "2 — pós-correção do achado A-1"],
    ["Data", date.today().strftime("%d/%m/%Y")],
    ["Endpoints analisados", "51 rotas em 10 blueprints"],
    ["Base", "backend/app/ (auth, alunos, instrutores, planos, mensalidades,\navaliacoes, configuracoes, dashboard, relatorios, portal)"],
], colWidths=[4.2*cm, 10.8*cm])
cap.setStyle(TableStyle([
    ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
    ("FONTNAME",(1,0),(1,-1),"Helvetica"),
    ("FONTSIZE",(0,0),(-1,-1),9),
    ("TEXTCOLOR",(0,0),(0,-1),AZUL),
    ("TEXTCOLOR",(1,0),(1,-1),CINZA),
    ("VALIGN",(0,0),(-1,-1),"TOP"),
    ("LINEBELOW",(0,0),(-1,-2),0.4,colors.HexColor("#e2e8f0")),
    ("TOPPADDING",(0,0),(-1,-1),6),
    ("BOTTOMPADDING",(0,0),(-1,-1),6),
]))
el.append(cap)
sp(50)
p("Documento técnico confidencial — uso interno do projeto.", "Rodape")
el.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 1. SUMÁRIO EXECUTIVO
# ══════════════════════════════════════════════════════════════════════════════
p("1. Sumário Executivo", "H1")
hr()
p("A aplicação apresenta um <b>nível de maturidade de segurança acima da média</b> para o "
  "estágio do projeto. A arquitetura de autenticação/autorização é sólida e foi claramente "
  "pensada: todas as 51 rotas (exceto o login público) exigem autenticação, a autorização por "
  "papel é aplicada via decorators, e os pontos clássicos de vazamento horizontal (BOLA/IDOR) "
  "nas leituras sensíveis por ID foram fechados com RLS por identidade do usuário.")
p("A análise identificou <b>1 falha concreta e explorável</b> (IDOR na exportação de PDF de "
  "avaliações físicas) — <b>já corrigida e coberta por testes de regressão</b> nesta revisão. "
  "Permanecem itens de hardening relevantes para o deploy em produção que se aproxima (rate limit "
  "não compartilhado entre workers e token em localStorage com CSP ainda em modo de observação). "
  "Não foram encontradas falhas críticas de injeção, exposição de segredos ou bypass de autenticação.")
sp(4)

# Tabela resumo de severidades
resumo = Table([
    [Paragraph("Severidade", "CelB"), Paragraph("Qtd.", "CelB"), Paragraph("Resumo", "CelB")],
    [Paragraph("CRÍTICO", "Badge"), "0", Paragraph("Nenhum item crítico identificado.", "Cel")],
    [Paragraph("ALTO", "Badge"),    "1", Paragraph("<b>[CORRIGIDO]</b> IDOR: instrutor exportava PDF de avaliação de qualquer aluno.", "Cel")],
    [Paragraph("MÉDIO", "Badge"),   "2", Paragraph("Rate limit em memória (multi-worker); token em localStorage + CSP report-only.", "Cel")],
    [Paragraph("BAIXO", "Badge"),   "3", Paragraph("Política de senha fraca; bucket público; uso de .single() em caminhos de 'não encontrado'.", "Cel")],
    [Paragraph("INFO", "Badge"),    "3", Paragraph("CORS em produção; leitura de planos por aluno; dependência externa do Gravatar no cadastro.", "Cel")],
], colWidths=[2.6*cm, 1.4*cm, 11*cm])
resumo.setStyle(TableStyle([
    ("BACKGROUND",(0,0),(-1,0),AZUL),
    ("BACKGROUND",(0,1),(0,1),CRIT),
    ("BACKGROUND",(0,2),(0,2),ALTO),
    ("BACKGROUND",(0,3),(0,3),MED),
    ("BACKGROUND",(0,4),(0,4),BAIXO),
    ("BACKGROUND",(0,5),(0,5),INFO),
    ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ("ALIGN",(1,0),(1,-1),"CENTER"),
    ("FONTSIZE",(1,1),(1,-1),9),
    ("FONTNAME",(1,1),(1,-1),"Helvetica-Bold"),
    ("GRID",(0,0),(-1,-1),0.5,colors.white),
    ("ROWBACKGROUNDS",(1,1),(-1,-1),[colors.white, CINZAC]),
    ("TOPPADDING",(0,0),(-1,-1),5),
    ("BOTTOMPADDING",(0,0),(-1,-1),5),
    ("LEFTPADDING",(0,0),(-1,-1),6),
]))
el.append(resumo)
sp(8)
p("<b>Conclusão executiva:</b> o IDOR do PDF de avaliações (único item de severidade Alta) <b>foi "
  "corrigido</b> nesta revisão, com testes de regressão. A prioridade restante é tratar o rate limit "
  "antes de subir em produção com múltiplos workers. O demais são melhorias incrementais de robustez. "
  "A base de segurança é confiável.", "Corpo")

el.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 2. ARQUITETURA DE SEGURANÇA
# ══════════════════════════════════════════════════════════════════════════════
p("2. Arquitetura de Autenticação e Autorização", "H1")
hr()
p("<b>Autenticação:</b> JWT emitido pelo Supabase Auth. O token é validado a cada requisição "
  "chamando o Supabase (<font face='Courier'>auth.get_user(token)</font>), o que respeita revogação "
  "no servidor — e não apenas a verificação local da assinatura. Contas desativadas perdem o acesso "
  "tanto no login quanto no <font face='Courier'>require_auth</font>, mesmo com token ainda válido.")
p("<b>Autorização por papel:</b> decorators <font face='Courier'>@require_auth</font> e "
  "<font face='Courier'>@require_role(...)</font> aplicam o controle de acesso. Os papéis são "
  "<i>admin</i>, <i>recepcionista</i>, <i>instrutor</i> e <i>aluno</i>.")
p("<b>Ponto-chave (e risco estrutural bem tratado):</b> o backend acessa o banco com a chave "
  "<font face='Courier'>service_role</font>, que <b>ignora o RLS</b> do PostgreSQL. Ou seja, a "
  "autorização real vive na aplicação (decorators) — as policies de RLS são defesa em profundidade. "
  "Para as leituras sensíveis por ID, o código abandona a service_role e usa "
  "<font face='Courier'>get_user_client(token)</font>, que reativa o RLS sob a identidade do usuário "
  "e fecha BOLA/IDOR (o banco decide quais linhas o usuário vê).")
p("<b>Isolamento de sessão:</b> o login usa um cliente anônimo isolado por requisição, evitando que "
  "a sessão de um usuário contamine o cliente global de service_role compartilhado entre requisições "
  "do Flask — uma armadilha comum e corretamente evitada aqui.")

sp(4)
p("Defesas transversais presentes", "H2")
defesas = [
    "Validação estrita de entrada com Pydantic (<font face='Courier'>extra=\"forbid\"</font> → mitiga mass-assignment); faixas numéricas espelham os CHECKs do banco.",
    "Cabeçalhos de segurança em toda resposta: X-Content-Type-Options, X-Frame-Options: DENY, Referrer-Policy, CSP restritiva na API e HSTS sob HTTPS.",
    "Respostas de erro 500 não vazam <font face='Courier'>str(e)</font> (apenas em modo debug).",
    "Upload de imagem sempre re-encodado com Pillow (descarta EXIF/polyglots); limite de tamanho em 3 camadas; caminho no Storage isolado por <font face='Courier'>user_id</font>.",
    "Troca de senha revalida a senha atual — token roubado não basta para trocá-la.",
    "Rate limiting via Flask-Limiter (limite específico e mais rígido no /login).",
    "CORS sem wildcard (origens explícitas); fail-fast se faltarem variáveis de ambiente obrigatórias.",
    "Sanitização do nome de arquivo no Content-Disposition e escape XML no título do PDF (anti-injeção).",
]
for d in defesas:
    el.append(Paragraph("• " + d, styles["CorpoP"]))
    sp(2)

el.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 3. MAPA DE ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════
p("3. Mapa de Endpoints e Controle de Acesso", "H1")
hr()
p("Inventário das 51 rotas, com método, autenticação exigida e observações de escopo. "
  "“RLS” indica que a rota usa o cliente sob a identidade do usuário (proteção contra IDOR).", "CorpoP")
sp(6)

def sec(nome):
    return [Paragraph(f"<b>{nome}</b>", "Cel"), "", "", ""]

linhas = [
    [Paragraph("Método", "CelB"), Paragraph("Rota", "CelB"), Paragraph("Acesso", "CelB"), Paragraph("Observação", "CelB")],

    sec("auth — /auth"),
    ["POST",   "/login",                 "Público", "Rate-limit (10/min); brute-force só limitado por IP"],
    ["POST",   "/logout",                "Autenticado", "Revoga a sessão (scope local)"],
    ["GET/PUT","/me",                     "Autenticado", "Próprio perfil"],
    ["POST",   "/change-password",       "Autenticado", "Revalida a senha atual"],
    ["POST/DEL","/me/avatar",            "Autenticado", "Pillow re-encode; pasta = user_id"],
    ["POST",   "/me/avatar/gravatar",    "Autenticado", "E-mail vem do backend"],

    sec("alunos — /alunos"),
    ["GET/POST","",                       "admin, recep.", "Listagem paginada; valida entrada"],
    ["GET",    "/{id}",                   "Autenticado", "RLS ✓ (fecha BOLA)"],
    ["PUT",    "/{id}",                   "admin, recep.", ""],
    ["PATCH",  "/{id}/status",           "admin, recep.", ""],
    ["GET",    "/{id}/planos",           "Autenticado", "RLS ✓"],
    ["POST",   "/{id}/planos",           "admin, recep.", "Bloqueia plano ativo duplicado"],
    ["GET",    "/{id}/planos/{v}",       "Autenticado", "RLS ✓"],
    ["PUT/DEL","/{id}/planos/{v}",       "admin, recep.", "Exclusão bloqueada se houver paga"],

    sec("instrutores — /instrutores"),
    ["GET",    "",                        "admin, recep.", ""],
    ["POST",   "",                        "admin", ""],
    ["GET",    "/{id}",                   "Autenticado", "RLS ✓ (protege salário)"],
    ["PUT",    "/{id}",                   "admin", ""],
    ["GET",    "/{id}/planos",           "admin, recep.", ""],
    ["POST/DEL","/{id}/planos[/{ip}]",   "admin", ""],

    sec("planos — /planos"),
    ["GET",    " e /{id}",                "Autenticado", "Não-admin vê só ativos; dado pouco sensível"],
    ["POST/PUT/PATCH","[/{id}][/ativo]",  "admin", ""],

    sec("mensalidades — /mensalidades"),
    ["GET",    "",                        "admin, recep.", "Valida 'mes' antes do banco"],
    ["GET",    "/{id}",                   "Autenticado", "RLS ✓"],
    ["POST",   "/{id}/pagar",            "admin, recep.", "Calcula juros; reativa aluno"],

    sec("avaliacoes — /avaliacoes"),
    ["GET",    "",                        "admin, instr., recep.", "Instrutor: filtrado aos seus alunos"],
    ["POST",   "",                        "admin, instr.", "Ownership do instrutor"],
    ["GET",    "/{id}",                   "admin, instr., recep.", "Ownership do instrutor (404)"],
    ["PUT",    "/{id}",                   "admin, instr.", "Ownership do instrutor"],
    ["DELETE", "/{id}",                   "admin", ""],
    ["GET",    "/{id}/pdf",              "admin, instr., recep.", "Ownership do instrutor (404) — corrigido (A-1)"],

    sec("configuracoes — /configuracoes"),
    ["GET",    "/usuarios",              "admin", "Lista profiles + e-mails do Auth"],
    ["PATCH",  "/usuarios/{id}/tipo",    "admin", "Não altera o próprio"],
    ["PATCH",  "/usuarios/{id}/status",  "admin", "Não desativa a si mesmo"],
    ["POST/DEL","/usuarios/{id}/avatar", "admin, recep.", "Foto de terceiros"],
    ["GET",    "/academia",              "Autenticado", "Leitura da config"],
    ["PUT",    "/academia",              "admin", ""],

    sec("dashboard — /dashboard"),
    ["GET",    "/alunos | /financeiro | /frequencia", "admin, recep.", "Agregações"],

    sec("relatorios — /relatorios"),
    ["GET",    "/alunos | /financeiro | /inadimplencia", "admin, recep.", "PDF/Excel; valida formato e mês"],

    sec("portal — /portal"),
    ["GET",    "/me | /mensalidades | /frequencias", "Autenticado", "Escopo = próprio aluno (profile_id)"],
    ["GET",    "/avaliacoes | /treino | /avisos", "Autenticado", "Escopo próprio; avisos são broadcast"],
]

tbl = Table(linhas, colWidths=[1.9*cm, 4.5*cm, 3.0*cm, 6.0*cm], repeatRows=1)
estilo = [
    ("BACKGROUND",(0,0),(-1,0),AZUL),
    ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ("FONTNAME",(0,1),(-1,-1),"Helvetica"),
    ("FONTSIZE",(0,1),(-1,-1),7.6),
    ("TEXTCOLOR",(0,1),(-1,-1),colors.HexColor("#1a202c")),
    ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#cbd5e0")),
    ("TOPPADDING",(0,0),(-1,-1),3),
    ("BOTTOMPADDING",(0,0),(-1,-1),3),
    ("LEFTPADDING",(0,0),(-1,-1),4),
    ("FONTNAME",(1,1),(1,-1),"Courier"),
]
# realça as linhas de seção (blueprint)
for i, ln in enumerate(linhas):
    if ln[1] == "" and ln[2] == "":
        estilo.append(("BACKGROUND",(0,i),(-1,i),colors.HexColor("#dbe4ee")))
        estilo.append(("SPAN",(0,i),(-1,i)))
        estilo.append(("FONTNAME",(0,i),(-1,i),"Helvetica-Bold"))
        estilo.append(("FONTSIZE",(0,i),(-1,i),8))
        estilo.append(("FONTNAME",(1,i),(1,i),"Helvetica-Bold"))
    # realça a linha do A-1 (agora corrigida) em verde
    if "corrigido (A-1)" in str(ln[3]):
        estilo.append(("BACKGROUND",(0,i),(-1,i),colors.HexColor("#e8f5e9")))
        estilo.append(("TEXTCOLOR",(3,i),(3,i),VERDE))
        estilo.append(("FONTNAME",(3,i),(3,i),"Helvetica-Bold"))
tbl.setStyle(TableStyle(estilo))
el.append(tbl)

el.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 4. ACHADOS DETALHADOS
# ══════════════════════════════════════════════════════════════════════════════
p("4. Achados Detalhados", "H1")
hr()

def achado(cod, titulo, sev, sev_cor, corpo, status=None):
    if status:
        cab = Table([[Paragraph(f"{cod} · {titulo}", "CelB"),
                      Paragraph(status, "Badge"), Paragraph(sev, "Badge")]],
                    colWidths=[10.0*cm, 2.5*cm, 2.5*cm])
        cab.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(0,0),AZUL2),
            ("BACKGROUND",(1,0),(1,0),VERDE),
            ("BACKGROUND",(2,0),(2,0),sev_cor),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(0,0),7),
        ]))
    else:
        cab = Table([[Paragraph(f"{cod} · {titulo}", "CelB"), Paragraph(sev, "Badge")]],
                    colWidths=[12.5*cm, 2.5*cm])
        cab.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(0,0),AZUL2),
            ("BACKGROUND",(1,0),(1,0),sev_cor),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
            ("LEFTPADDING",(0,0),(0,0),7),
        ]))
    el.append(cab)
    sp(4)
    for label, txt in corpo:
        el.append(Paragraph(f"<b>{label}:</b> {txt}", styles["CorpoP"]))
        sp(2)
    sp(8)

achado("A-1", "IDOR na exportação de PDF de avaliações físicas", "ALTO", ALTO, [
    ("Local", "backend/app/avaliacoes/routes.py — <font face='Courier'>GET /avaliacoes/&lt;id&gt;/pdf</font> (exportar_pdf)"),
    ("Descrição", "O endpoint que devolve a avaliação em JSON (<font face='Courier'>GET /avaliacoes/&lt;id&gt;</font>) "
     "verifica o ownership do instrutor — um instrutor só vê avaliações de alunos dos seus planos, recebendo 404 caso "
     "contrário. <b>O endpoint de PDF não faz essa verificação.</b> Ele usa a service_role (sem RLS) e só exige o papel "
     "instrutor. Logo, qualquer instrutor autenticado consegue exportar o PDF de <b>qualquer</b> avaliação do sistema, "
     "informando apenas o ID."),
    ("Impacto", "Quebra de isolamento horizontal entre instrutores e exposição de PII e dados de saúde: o PDF contém "
     "nome do aluno, <b>CPF</b>, peso, percentual de gordura, circunferências e diâmetros corporais de alunos que não "
     "pertencem ao instrutor."),
    ("Exploração", "Trivial — basta estar autenticado como instrutor e iterar/adivinhar IDs (UUID) de avaliações. "
     "Não há barreira de RLS porque a rota usa a service_role."),
    ("Correção sugerida", "Replicar o mesmo guard do endpoint JSON: após carregar a avaliação, se "
     "<font face='Courier'>g.user_tipo == 'instrutor'</font> e o <font face='Courier'>aluno_id</font> não estiver em "
     "<font face='Courier'>_alunos_do_instrutor(g.user_id)</font>, retornar 404."),
    ("Status — CORRIGIDO", "<font color='#2e7d32'><b>Remediado nesta revisão.</b></font> O guard de ownership do "
     "instrutor foi adicionado ao <font face='Courier'>exportar_pdf</font> (devolve 404 para avaliações fora do "
     "escopo do instrutor). Cobertura por 2 testes de regressão em <font face='Courier'>tests/test_avaliacoes.py</font> "
     "(instrutor fora do escopo → 404; instrutor do escopo → 200). Suíte completa: 187 testes passando."),
], status="CORRIGIDO")

achado("M-1", "Rate limit em memória — frágil sob múltiplos workers (produção)", "MÉDIO", MED, [
    ("Local", "backend/app/config.py — <font face='Courier'>RATELIMIT_STORAGE_URI = 'memory://'</font>"),
    ("Descrição", "O Flask-Limiter está configurado com armazenamento em memória do processo. O deploy de produção "
     "previsto usa gunicorn com Docker — tipicamente vários workers. Com 'memory://', cada worker mantém seu próprio "
     "contador, então o limite de 10 logins/min vale por worker: com N workers, o atacante tem efetivamente N×10 "
     "tentativas/min. O brute-force protection do /login fica diluído."),
    ("Impacto", "Enfraquecimento da proteção contra força bruta de credenciais em produção."),
    ("Correção sugerida", "Definir <font face='Courier'>RATELIMIT_STORAGE_URI=redis://...</font> (storage compartilhado) "
     "antes de subir com múltiplos workers, e adicionar o redis ao docker-compose. Já previsto no .env.example; "
     "elevar a prioridade dado o deploy iminente."),
])

achado("M-2", "Token JWT em localStorage com CSP ainda em modo report-only", "MÉDIO", MED, [
    ("Local", "Frontend (Next.js) — armazenamento de sessão + frontend/proxy.js (CSP)"),
    ("Descrição", "O access token fica no localStorage (acessível por JavaScript). Uma falha de XSS permitiria exfiltrar "
     "o token. A mitigação — Content-Security-Policy com nonce — já existe, porém em <b>modo report-only</b> "
     "(<font face='Courier'>REPORT_ONLY = true</font>), ou seja, ainda não bloqueia, apenas reporta violações."),
    ("Impacto", "Janela de risco a roubo de sessão caso surja um XSS; a CSP não está efetivamente protegendo enquanto "
     "estiver em observação."),
    ("Correção sugerida", "Validar a CSP tela a tela no navegador e trocar para modo de bloqueio "
     "(<font face='Courier'>REPORT_ONLY = false</font>). Avaliar mover o token para cookie httpOnly + SameSite no futuro "
     "(exige rever o fluxo de envio do Bearer ao Flask)."),
])

achado("B-1", "Política de senha permissiva (mínimo de 6 caracteres)", "BAIXO", BAIXO, [
    ("Local", "backend/app/schemas.py — <font face='Courier'>Senha = Field(min_length=6, max_length=128)</font>"),
    ("Descrição", "Senhas de 6 caracteres, sem exigência de complexidade. Aceitável para um MVP, mas baixo para contas "
     "administrativas que controlam dados financeiros e PII."),
    ("Correção sugerida", "Elevar o mínimo para 8+ caracteres e ativar a proteção contra senhas vazadas (leaked "
     "password protection) no painel do Supabase Auth."),
])

achado("B-2", "Bucket de avatares público", "BAIXO", BAIXO, [
    ("Local", "Supabase Storage — bucket 'avatars' (público) / app/auth/avatar.py"),
    ("Descrição", "As fotos de perfil são servidas por URL pública. O caminho inclui um UUID aleatório (não enumerável), "
     "mas qualquer pessoa com a URL acessa a imagem, sem autenticação."),
    ("Correção sugerida", "Se as fotos forem consideradas sensíveis, migrar para bucket privado com signed URLs de "
     "curta duração. Caso contrário, documentar a decisão de mantê-lo público como aceitável."),
])

achado("B-3", "Uso de .single() em caminhos de 'não encontrado' gera 500 em vez de 404", "BAIXO", BAIXO, [
    ("Local", "Vários: avaliacoes (buscar/atualizar/pdf), mensalidades (pagar), planos (buscar), alunos (vincular_plano), login"),
    ("Descrição", "<font face='Courier'>.single()</font> lança exceção quando não há linha (PGRST116), antes da checagem "
     "<font face='Courier'>if not result.data</font>. Em recursos inexistentes, isso resulta em HTTP 500 genérico em vez "
     "de 404. Não há vazamento (o handler 500 oculta detalhes), então o impacto é de robustez/consistência, não de "
     "exposição."),
    ("Correção sugerida", "Padronizar para <font face='Courier'>.maybe_single()</font> nesses caminhos de leitura, "
     "como já é feito na maior parte do código."),
])

achado("I-1", "Hardening de produção: CORS, Gravatar externo e leitura de planos", "INFO", INFO, [
    ("CORS", "<font face='Courier'>ALLOWED_ORIGINS</font> tem default localhost. Em produção, definir explicitamente as "
     "origens do front; nunca usar wildcard com <font face='Courier'>supports_credentials=True</font>."),
    ("Gravatar", "O cadastro de aluno e o avatar consultam gravatar.com (GET externo, timeout 5s) — dependência de "
     "terceiro no caminho de escrita e leve enumeração de e-mail no Gravatar. Considerar tornar opcional/assíncrono."),
    ("Planos", "<font face='Courier'>GET /planos/&lt;id&gt;</font> é legível por qualquer autenticado (inclusive aluno) e "
     "expõe nomes de instrutores vinculados. Dado pouco sensível — apenas registrar como decisão consciente."),
])

el.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# 5. PONTOS FORTES
# ══════════════════════════════════════════════════════════════════════════════
p("5. Pontos Fortes (o que já está bem feito)", "H1")
hr()
fortes = [
    "<b>BOLA/IDOR fechado nas leituras por ID sensíveis</b> (alunos, instrutores, mensalidades) via RLS por identidade — padrão correto e bem aplicado.",
    "<b>Isolamento da service_role</b>: nunca usada para login; cliente anônimo isolado por requisição evita vazamento de sessão entre requisições.",
    "<b>Validação de entrada estrita</b> (Pydantic, extra=\"forbid\") em todas as escritas — anti mass-assignment e anti-lixo.",
    "<b>Sanitização de imagem real</b> com Pillow (re-encode descarta EXIF/polyglots) e limite de tamanho em três camadas.",
    "<b>Troca de senha revalida a senha atual</b> — token válido roubado não é suficiente.",
    "<b>Autoria de avaliações forçada no servidor</b> para instrutores (não confia no cliente).",
    "<b>Erros não vazam detalhes internos</b> (str(e) só em debug); cabeçalhos de segurança padronizados em toda resposta.",
    "<b>Contas desativadas bloqueadas</b> no login e em cada requisição; fail-fast sem variáveis obrigatórias.",
    "<b>Unicidade garantida no banco</b> (índices únicos parciais) além da checagem na aplicação — defesa em profundidade contra corrida.",
    "<b>Anti-injeção em downloads</b>: nome de arquivo saneado no Content-Disposition e escape XML no título do PDF.",
]
for f in fortes:
    el.append(Paragraph("✓ " + f, styles["CorpoP"]))
    sp(3)

sp(10)
p("6. Plano de Ação Priorizado", "H1")
hr()
plano = [
    [Paragraph("Prioridade", "CelB"), Paragraph("Ação", "CelB"), Paragraph("Item", "CelB")],
    [Paragraph("<font color='#2e7d32'><b>✓ Concluído</b></font>", "Cel"),  Paragraph("Guard de ownership do instrutor adicionado ao <font face='Courier'>GET /avaliacoes/&lt;id&gt;/pdf</font> (com testes).", "Cel"), "A-1"],
    [Paragraph("1 — Antes do deploy", "Cel"), Paragraph("Configurar Redis como storage do rate limit (compartilhado entre workers).", "Cel"), "M-1"],
    [Paragraph("2 — Antes do deploy", "Cel"), Paragraph("Definir ALLOWED_ORIGINS de produção; revisar HSTS/HTTPS na borda (Nginx/Cloudflare).", "Cel"), "I-1"],
    [Paragraph("3 — Curto prazo", "Cel"), Paragraph("Sair do CSP report-only para modo de bloqueio após validação.", "Cel"), "M-2"],
    [Paragraph("4 — Curto prazo", "Cel"), Paragraph("Elevar mínimo de senha e ativar proteção de senha vazada no Supabase.", "Cel"), "B-1"],
    [Paragraph("5 — Backlog", "Cel"), Paragraph("Padronizar .maybe_single(); revisar bucket de avatares; Gravatar opcional.", "Cel"), "B-2/B-3"],
]
ptbl = Table(plano, colWidths=[3.2*cm, 9.8*cm, 2.0*cm])
ptbl.setStyle(TableStyle([
    ("BACKGROUND",(0,0),(-1,0),AZUL),
    ("GRID",(0,0),(-1,-1),0.4,colors.HexColor("#cbd5e0")),
    ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
    ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, CINZAC]),
    ("FONTNAME",(2,1),(2,-1),"Helvetica-Bold"),
    ("FONTSIZE",(2,1),(2,-1),8),
    ("ALIGN",(2,0),(2,-1),"CENTER"),
    ("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5),
    ("LEFTPADDING",(0,0),(-1,-1),5),
]))
el.append(ptbl)
sp(12)
p("<i>Observação metodológica: análise estática (revisão de código-fonte), sem execução de testes "
  "de intrusão dinâmicos. Nenhuma alteração foi feita na aplicação. As severidades seguem uma escala "
  "qualitativa (Crítico / Alto / Médio / Baixo / Informativo) considerando impacto e facilidade de "
  "exploração no contexto do produto.</i>", "CorpoP")

# ── Rodapé/numeração ──────────────────────────────────────────────────────────
def rodape(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(CINZA)
    canvas.drawString(2*cm, 1.1*cm, "Relatório de Segurança — Gestão de Academias · Confidencial")
    canvas.drawRightString(19*cm, 1.1*cm, f"Página {doc.page}")
    canvas.setStrokeColor(colors.HexColor("#cbd5e0"))
    canvas.line(2*cm, 1.4*cm, 19*cm, 1.4*cm)
    canvas.restoreState()

doc = SimpleDocTemplate(
    SAIDA, pagesize=A4,
    leftMargin=2*cm, rightMargin=2*cm, topMargin=1.8*cm, bottomMargin=1.8*cm,
    title="Relatório de Segurança — Gestão de Academias",
    author="Análise de Segurança",
)
doc.build(el, onFirstPage=lambda c, d: None, onLaterPages=rodape)
print("PDF gerado em:", SAIDA)
