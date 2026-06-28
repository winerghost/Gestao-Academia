from datetime import date
from calendar import monthrange
from flask import Blueprint, request, send_file, jsonify
from ..supabase_client import supabase
from ..auth.middleware import require_role
from ..validation import mes_valido
from .pdf import gerar_pdf
from .excel import gerar_excel

relatorios_bp = Blueprint("relatorios", __name__, url_prefix="/relatorios")

MIME_PDF = "application/pdf"
MIME_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _responder(buffer, formato: str, nome_base: str):
    hoje = date.today().strftime("%Y%m%d")
    if formato == "pdf":
        return send_file(buffer, mimetype=MIME_PDF, as_attachment=True,
                         download_name=f"{nome_base}_{hoje}.pdf")
    return send_file(buffer, mimetype=MIME_EXCEL, as_attachment=True,
                     download_name=f"{nome_base}_{hoje}.xlsx")


def _validar_formato(formato: str):
    if formato not in ("pdf", "excel"):
        return jsonify({"error": "Parâmetro 'formato' deve ser 'pdf' ou 'excel'"}), 400
    return None


def _intervalo_mes(mes: str | None) -> tuple[str, str]:
    if mes:
        ano, m = int(mes[:4]), int(mes[5:7])
    else:
        hoje = date.today()
        ano, m = hoje.year, hoje.month
    ultimo = monthrange(ano, m)[1]
    return f"{ano}-{m:02d}-01", f"{ano}-{m:02d}-{ultimo:02d}"


def _gerar(titulo, headers, rows, formato, nome_base):
    buffer = gerar_pdf(titulo, headers, rows) if formato == "pdf" else gerar_excel(titulo, headers, rows)
    return _responder(buffer, formato, nome_base)


# ── Relatório de alunos ───────────────────────────────────────────────────────

@relatorios_bp.get("/alunos")
@require_role("admin", "recepcionista")
def relatorio_alunos():
    formato = request.args.get("formato", "pdf")
    status = request.args.get("status")

    erro = _validar_formato(formato)
    if erro:
        return erro

    query = supabase.table("alunos").select(
        "cpf, status, created_at, profiles(nome, telefone), aluno_planos(planos(nome))"
    )
    if status:
        query = query.eq("status", status)

    alunos = query.order("created_at", desc=False).execute().data

    headers = ["Nome", "CPF", "Telefone", "Status", "Planos", "Cadastro"]
    rows = []
    for a in alunos:
        profile = a.get("profiles") or {}
        planos_nomes = ", ".join(
            ap["planos"]["nome"]
            for ap in (a.get("aluno_planos") or [])
            if ap.get("planos")
        ) or "—"
        rows.append([
            profile.get("nome", "—"),
            a["cpf"],
            profile.get("telefone") or "—",
            a["status"].capitalize(),
            planos_nomes,
            a["created_at"][:10],
        ])

    titulo = f"Relatório de Alunos{' — ' + status.capitalize() if status else ''}"
    return _gerar(titulo, headers, rows, formato, "alunos")


# ── Relatório financeiro ──────────────────────────────────────────────────────

@relatorios_bp.get("/financeiro")
@require_role("admin", "recepcionista")
def relatorio_financeiro():
    formato = request.args.get("formato", "pdf")
    mes = request.args.get("mes")  # ex: 2026-06

    erro = _validar_formato(formato)
    if erro:
        return erro

    # Mês malformado quebraria o int(mes[:4]) em _intervalo_mes (500). Valida antes.
    if mes is not None and not mes_valido(mes):
        return jsonify({"error": "Parâmetro 'mes' deve estar no formato AAAA-MM"}), 400

    inicio, fim = _intervalo_mes(mes)
    mensalidades = (
        supabase.table("mensalidades")
        .select("valor, juros, valor_total, data_vencimento, data_pagamento, status, "
                "aluno_planos(planos(nome), alunos(profiles(nome)))")
        .gte("data_vencimento", inicio)
        .lte("data_vencimento", fim)
        .order("data_vencimento")
        .execute()
        .data
    )

    headers = ["Aluno", "Plano", "Vencimento", "Valor (R$)", "Juros (R$)", "Total (R$)", "Status", "Pagamento"]
    rows = []
    for m in mensalidades:
        ap = m.get("aluno_planos") or {}
        profile = (ap.get("alunos") or {}).get("profiles") or {}
        plano = ap.get("planos") or {}
        rows.append([
            profile.get("nome", "—"),
            plano.get("nome", "—"),
            m["data_vencimento"],
            f"{m['valor']:.2f}",
            f"{m['juros']:.2f}",
            f"{m['valor_total']:.2f}",
            m["status"].capitalize(),
            m.get("data_pagamento") or "—",
        ])

    ref = mes or date.today().strftime("%Y-%m")
    titulo = f"Relatório Financeiro — {ref}"
    return _gerar(titulo, headers, rows, formato, "financeiro")


# ── Relatório de inadimplência ────────────────────────────────────────────────

@relatorios_bp.get("/inadimplencia")
@require_role("admin", "recepcionista")
def relatorio_inadimplencia():
    formato = request.args.get("formato", "pdf")

    erro = _validar_formato(formato)
    if erro:
        return erro

    atrasadas = (
        supabase.table("mensalidades")
        .select("valor, data_vencimento, "
                "aluno_planos(planos(nome), alunos(cpf, profiles(nome, telefone)))")
        .eq("status", "atrasada")
        .order("data_vencimento")
        .execute()
        .data
    )

    hoje = date.today()
    headers = ["Aluno", "CPF", "Telefone", "Plano", "Vencimento", "Dias em atraso", "Valor (R$)"]
    rows = []
    for m in atrasadas:
        ap = m.get("aluno_planos") or {}
        aluno = ap.get("alunos") or {}
        profile = aluno.get("profiles") or {}
        plano = ap.get("planos") or {}
        vcto = date.fromisoformat(m["data_vencimento"])
        dias = (hoje - vcto).days
        rows.append([
            profile.get("nome", "—"),
            aluno.get("cpf", "—"),
            profile.get("telefone") or "—",
            plano.get("nome", "—"),
            m["data_vencimento"],
            dias,
            f"{m['valor']:.2f}",
        ])

    return _gerar(f"Relatório de Inadimplência — {hoje.strftime('%d/%m/%Y')}",
                  headers, rows, formato, "inadimplencia")
