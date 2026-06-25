from datetime import date, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from ..supabase_client import supabase


# ── Helpers ───────────────────────────────────────────────────────────────────

def criar_mensalidade(aluno_plano_id: str, valor: float, data_vencimento: date):
    supabase.table("mensalidades").insert({
        "aluno_plano_id": aluno_plano_id,
        "valor": valor,
        "juros": 0,
        "data_vencimento": data_vencimento.isoformat(),
        "status": "pendente",
    }).execute()


# ── Jobs ──────────────────────────────────────────────────────────────────────

def job_atualizar_inadimplencia():
    """
    Roda diariamente à meia-noite.
    1. Marca como 'atrasada' toda mensalidade pendente com vencimento anterior a hoje.
    2. Marca como 'inadimplente' todo aluno que tem mensalidade atrasada.
    3. Reativa alunos que quitaram todas as mensalidades atrasadas.
    """
    hoje = date.today().isoformat()

    # 1. Pendentes vencidas → atrasadas
    supabase.table("mensalidades").update({"status": "atrasada"}).eq(
        "status", "pendente"
    ).lt("data_vencimento", hoje).execute()

    # 2. Alunos com atrasadas → inadimplente
    atrasadas = (
        supabase.table("mensalidades")
        .select("aluno_planos(aluno_id)")
        .eq("status", "atrasada")
        .execute()
    )
    ids_inadimplentes = {
        r["aluno_planos"]["aluno_id"]
        for r in atrasadas.data
        if r.get("aluno_planos")
    }
    for aluno_id in ids_inadimplentes:
        supabase.table("alunos").update({"status": "inadimplente"}).eq(
            "id", aluno_id
        ).execute()

    # 3. Alunos sem atrasadas que estavam inadimplentes → ativo
    todos_inadimplentes = (
        supabase.table("alunos")
        .select("id")
        .eq("status", "inadimplente")
        .execute()
    )
    for aluno in todos_inadimplentes.data:
        aluno_id = aluno["id"]
        if aluno_id not in ids_inadimplentes:
            supabase.table("alunos").update({"status": "ativo"}).eq(
                "id", aluno_id
            ).execute()


def job_gerar_mensalidades():
    """
    Roda diariamente à meia-noite.
    Para cada aluno_plano ativo, gera a próxima mensalidade quando a última
    vence em até 5 dias — garantindo que o aluno sempre tenha uma mensalidade futura.
    """
    hoje = date.today()
    horizonte = (hoje + timedelta(days=5)).isoformat()

    planos_ativos = (
        supabase.table("aluno_planos")
        .select("id, data_fim, planos(valor)")
        .eq("status", "ativo")
        .execute()
    )

    for ap in planos_ativos.data:
        ultima = (
            supabase.table("mensalidades")
            .select("data_vencimento")
            .eq("aluno_plano_id", ap["id"])
            .order("data_vencimento", desc=True)
            .limit(1)
            .execute()
        )
        if not ultima.data:
            continue

        ultima_vcto = date.fromisoformat(ultima.data[0]["data_vencimento"])
        proxima_vcto = ultima_vcto + timedelta(days=30)

        # Não gera se já existe mensalidade futura para esta data
        if proxima_vcto.isoformat() > horizonte:
            continue

        # Não gera se o plano já encerrou
        data_fim = ap.get("data_fim")
        if data_fim and proxima_vcto > date.fromisoformat(data_fim):
            continue

        criar_mensalidade(ap["id"], ap["planos"]["valor"], proxima_vcto)


# ── Scheduler ─────────────────────────────────────────────────────────────────

def iniciar_scheduler():
    from ..notificacoes.jobs import job_notificar_vencimentos, job_notificar_atrasadas

    scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
    scheduler.add_job(job_atualizar_inadimplencia, "cron", hour=0, minute=5)
    scheduler.add_job(job_gerar_mensalidades,      "cron", hour=0, minute=10)
    scheduler.add_job(job_notificar_vencimentos,   "cron", hour=8, minute=0)
    scheduler.add_job(job_notificar_atrasadas,     "cron", hour=8, minute=15)
    scheduler.start()
    return scheduler
