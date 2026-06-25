from datetime import date, timedelta
from calendar import monthrange
from flask import Blueprint, jsonify
from ..supabase_client import supabase
from ..auth.middleware import require_role

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


def _intervalo_mes(hoje: date) -> tuple[str, str]:
    """Retorna (primeiro_dia, ultimo_dia) do mês no formato ISO."""
    ultimo = monthrange(hoje.year, hoje.month)[1]
    return (
        date(hoje.year, hoje.month, 1).isoformat(),
        date(hoje.year, hoje.month, ultimo).isoformat(),
    )


# ── Dashboard de alunos ───────────────────────────────────────────────────────

@dashboard_bp.get("/alunos")
@require_role("admin", "recepcionista")
def dashboard_alunos():
    hoje = date.today()
    inicio_mes, _ = _intervalo_mes(hoje)

    alunos = supabase.table("alunos").select("id, status, created_at").execute().data

    total = len(alunos)
    por_status = {"ativo": 0, "inativo": 0, "inadimplente": 0}
    novos_no_mes = 0

    for a in alunos:
        por_status[a["status"]] = por_status.get(a["status"], 0) + 1
        if a["created_at"][:10] >= inicio_mes:
            novos_no_mes += 1

    # Distribuição por plano (aluno_planos ativos)
    ap = (
        supabase.table("aluno_planos")
        .select("planos(nome)")
        .eq("status", "ativo")
        .execute()
        .data
    )
    por_plano: dict[str, int] = {}
    for item in ap:
        nome = item.get("planos", {}).get("nome", "Desconhecido")
        por_plano[nome] = por_plano.get(nome, 0) + 1

    return jsonify({
        "total": total,
        "ativos": por_status["ativo"],
        "inativos": por_status["inativo"],
        "inadimplentes": por_status["inadimplente"],
        "novos_no_mes": novos_no_mes,
        "por_plano": [{"plano": k, "total": v} for k, v in sorted(por_plano.items())],
    })


# ── Dashboard financeiro ──────────────────────────────────────────────────────

@dashboard_bp.get("/financeiro")
@require_role("admin", "recepcionista")
def dashboard_financeiro():
    hoje = date.today()
    inicio_mes, fim_mes = _intervalo_mes(hoje)

    # Mensalidades com vencimento no mês atual
    mens_mes = (
        supabase.table("mensalidades")
        .select("status, valor, valor_total")
        .gte("data_vencimento", inicio_mes)
        .lte("data_vencimento", fim_mes)
        .execute()
        .data
    )

    receita_paga = round(sum(m["valor_total"] for m in mens_mes if m["status"] == "paga"), 2)
    receita_prevista = round(sum(m["valor"] for m in mens_mes), 2)
    qtd_pagas = sum(1 for m in mens_mes if m["status"] == "paga")
    qtd_pendentes = sum(1 for m in mens_mes if m["status"] == "pendente")
    qtd_atrasadas_mes = sum(1 for m in mens_mes if m["status"] == "atrasada")

    # Total em aberto (todas as atrasadas, não só do mês)
    atrasadas = (
        supabase.table("mensalidades")
        .select("valor")
        .eq("status", "atrasada")
        .execute()
        .data
    )
    total_inadimplente = round(sum(m["valor"] for m in atrasadas), 2)

    # Taxa de inadimplência (alunos inadimplentes / total)
    alunos = supabase.table("alunos").select("status").execute().data
    total_alunos = len(alunos)
    inadimplentes = sum(1 for a in alunos if a["status"] == "inadimplente")
    taxa = round((inadimplentes / total_alunos * 100), 2) if total_alunos else 0.0

    return jsonify({
        "mes_referencia": f"{hoje.year}-{hoje.month:02d}",
        "receita_paga": receita_paga,
        "receita_prevista": receita_prevista,
        "total_inadimplente": total_inadimplente,
        "mensalidades_pagas": qtd_pagas,
        "mensalidades_pendentes": qtd_pendentes,
        "mensalidades_atrasadas": qtd_atrasadas_mes,
        "taxa_inadimplencia": taxa,
    })


# ── Dashboard de frequência ───────────────────────────────────────────────────

@dashboard_bp.get("/frequencia")
@require_role("admin", "recepcionista")
def dashboard_frequencia():
    hoje = date.today()
    inicio_mes, _ = _intervalo_mes(hoje)
    sete_dias_atras = (hoje - timedelta(days=7)).isoformat()

    # Entradas hoje
    freq_hoje = (
        supabase.table("frequencias")
        .select("id")
        .gte("data_hora", f"{hoje.isoformat()}T00:00:00")
        .execute()
        .data
    )

    # Entradas no mês
    freq_mes = (
        supabase.table("frequencias")
        .select("id")
        .gte("data_hora", f"{inicio_mes}T00:00:00")
        .execute()
        .data
    )

    # Alunos com frequência habilitada que não apareceram nos últimos 7 dias
    alunos_com_freq = (
        supabase.table("alunos")
        .select("id")
        .eq("frequencia_habilitada", True)
        .eq("status", "ativo")
        .execute()
        .data
    )
    freq_recente = (
        supabase.table("frequencias")
        .select("aluno_id")
        .gte("data_hora", f"{sete_dias_atras}T00:00:00")
        .execute()
        .data
    )
    ids_com_freq_recente = {f["aluno_id"] for f in freq_recente}
    sem_frequencia = sum(
        1 for a in alunos_com_freq if a["id"] not in ids_com_freq_recente
    )

    return jsonify({
        "entradas_hoje": len(freq_hoje),
        "entradas_mes": len(freq_mes),
        "alunos_sem_frequencia_7_dias": sem_frequencia,
    })
