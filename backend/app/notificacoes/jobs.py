import logging
from datetime import date, timedelta
from ..supabase_client import supabase
from .email import enviar_email, template_vencimento, template_atrasada

logger = logging.getLogger(__name__)


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
    Envia e-mail para alunos com mensalidade vencendo amanhã.
    """
    amanha = (date.today() + timedelta(days=1)).isoformat()

    mensalidades = (
        supabase.table("mensalidades")
        .select(
            "valor, data_vencimento, "
            "aluno_planos(planos(nome), alunos(profile_id, profiles(nome)))"
        )
        .eq("data_vencimento", amanha)
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
    Envia e-mail para alunos com mensalidades em atraso.
    """
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
