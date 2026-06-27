import logging
from datetime import date, timedelta
from ..supabase_client import supabase
from .email import enviar_email, template_vencimento, template_atrasada

logger = logging.getLogger(__name__)

# Defaults usados quando a tabela de config ainda não existe (migration 006
# não rodada) ou a leitura falha — preserva o comportamento original.
_CONFIG_PADRAO = {
    "notif_lembrete_ativo": True,
    "notif_dias_antes": 1,
    "notif_atraso_ativo": True,
}


def _config_notificacoes() -> dict:
    """Lê os parâmetros de notificação da configuração da academia."""
    try:
        data = (
            supabase.table("academia_config")
            .select("notif_lembrete_ativo, notif_dias_antes, notif_atraso_ativo")
            .eq("id", 1)
            .single()
            .execute()
            .data
        )
        return data or _CONFIG_PADRAO
    except Exception:
        logger.warning("Não foi possível ler academia_config; usando padrões")
        return _CONFIG_PADRAO


def _email_do_usuario(profile_id: str) -> str | None:
    """Busca o e-mail do usuário via Supabase Auth."""
    try:
        resp = supabase.auth.admin.get_user_by_id(profile_id)
        return resp.user.email
    except Exception:
        logger.warning("Não foi possível obter e-mail do usuário %s", profile_id)
        return None


def job_notificar_vencimentos():
    """
    Roda diariamente às 08:00.
    Envia e-mail para alunos com mensalidade vencendo dentro de
    `notif_dias_antes` dias (configurável). Desativável via config.
    """
    config = _config_notificacoes()
    if not config.get("notif_lembrete_ativo", True):
        logger.info("Lembrete de vencimento desativado nas configurações; pulando.")
        return

    dias_antes = config.get("notif_dias_antes", 1)
    alvo = (date.today() + timedelta(days=dias_antes)).isoformat()

    mensalidades = (
        supabase.table("mensalidades")
        .select(
            "valor, data_vencimento, "
            "aluno_planos(planos(nome), alunos(profile_id, profiles(nome)))"
        )
        .eq("data_vencimento", alvo)
        .eq("status", "pendente")
        .execute()
        .data
    )

    for m in mensalidades:
        ap = m.get("aluno_planos") or {}
        aluno = ap.get("alunos") or {}
        profile_id = aluno.get("profile_id")
        nome = (aluno.get("profiles") or {}).get("nome", "Aluno")
        plano = (ap.get("planos") or {}).get("nome", "")

        if not profile_id:
            continue

        email = _email_do_usuario(profile_id)
        if not email:
            continue

        enviar_email(
            email,
            f"Lembrete: sua mensalidade vence amanhã — {plano}",
            template_vencimento(nome, plano, m["data_vencimento"], m["valor"]),
        )


def job_notificar_atrasadas():
    """
    Roda diariamente às 08:15.
    Envia e-mail para alunos com mensalidades em atraso. Desativável via config.
    """
    if not _config_notificacoes().get("notif_atraso_ativo", True):
        logger.info("Aviso de atraso desativado nas configurações; pulando.")
        return

    hoje = date.today()

    atrasadas = (
        supabase.table("mensalidades")
        .select(
            "valor, data_vencimento, "
            "aluno_planos(planos(nome), alunos(profile_id, profiles(nome)))"
        )
        .eq("status", "atrasada")
        .execute()
        .data
    )

    for m in atrasadas:
        ap = m.get("aluno_planos") or {}
        aluno = ap.get("alunos") or {}
        profile_id = aluno.get("profile_id")
        nome = (aluno.get("profiles") or {}).get("nome", "Aluno")
        plano = (ap.get("planos") or {}).get("nome", "")
        dias = (hoje - date.fromisoformat(m["data_vencimento"])).days

        if not profile_id:
            continue

        email = _email_do_usuario(profile_id)
        if not email:
            continue

        enviar_email(
            email,
            f"Mensalidade em atraso — {plano}",
            template_atrasada(nome, plano, m["data_vencimento"], m["valor"], dias),
        )
