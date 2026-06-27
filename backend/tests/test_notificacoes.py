from unittest.mock import patch, MagicMock, call
import pytest
from app import create_app
from app.notificacoes.email import enviar_email, template_vencimento, template_atrasada
from app.notificacoes.jobs import job_notificar_vencimentos, job_notificar_atrasadas


@pytest.fixture
def app_ctx():
    app = create_app()
    app.config["TESTING"] = True
    with app.app_context():
        yield


# ── enviar_email ──────────────────────────────────────────────────────────────

def test_enviar_email_sem_credenciais(app_ctx):
    with patch("app.notificacoes.email.Config") as mock_cfg:
        mock_cfg.EMAIL_USER = None
        mock_cfg.EMAIL_PASSWORD = None
        mock_cfg.EMAIL_FROM = None
        resultado = enviar_email("dest@test.com", "Assunto", "<p>Corpo</p>")
        assert resultado is False


def test_enviar_email_com_credenciais(app_ctx):
    with patch("app.notificacoes.email.Config") as mock_cfg, \
         patch("app.notificacoes.email.smtplib.SMTP") as mock_smtp:
        mock_cfg.EMAIL_USER = "academia@gmail.com"
        mock_cfg.EMAIL_PASSWORD = "senha-app"
        mock_cfg.EMAIL_FROM = "academia@gmail.com"
        mock_cfg.EMAIL_HOST = "smtp.gmail.com"
        mock_cfg.EMAIL_PORT = 587

        smtp_instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = smtp_instance

        resultado = enviar_email("aluno@test.com", "Teste", "<p>Olá</p>")
        assert resultado is True
        smtp_instance.starttls.assert_called_once()
        smtp_instance.login.assert_called_once_with("academia@gmail.com", "senha-app")


# ── Templates ─────────────────────────────────────────────────────────────────

def test_template_vencimento_contem_dados():
    html = template_vencimento("João", "Musculação", "2026-06-25", 99.90)
    assert "João" in html
    assert "Musculação" in html
    assert "2026-06-25" in html
    assert "99.90" in html


def test_template_atrasada_contem_juros():
    html = template_atrasada("Maria", "Natação", "2026-06-01", 100.0, 30)
    assert "Maria" in html
    assert "30" in html
    assert "2.00" in html  # juros: 100 * 2% * (30/30) = 2.00


# ── Jobs ──────────────────────────────────────────────────────────────────────

_CONFIG_ATIVA = {
    "notif_lembrete_ativo": True,
    "notif_dias_antes": 1,
    "notif_atraso_ativo": True,
}


def test_job_notificar_vencimentos_sem_mensalidades():
    with patch("app.notificacoes.jobs.supabase") as mock_supa, \
         patch("app.notificacoes.jobs._config_notificacoes", return_value=_CONFIG_ATIVA):
        mock_supa.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        job_notificar_vencimentos()  # Não deve lançar exceção


def test_job_notificar_atrasadas_envia_email():
    with patch("app.notificacoes.jobs.supabase") as mock_supa, \
         patch("app.notificacoes.jobs.enviar_email") as mock_email, \
         patch("app.notificacoes.jobs._config_notificacoes", return_value=_CONFIG_ATIVA), \
         patch("app.notificacoes.jobs._email_do_usuario", return_value="aluno@test.com"):

        mock_supa.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                "valor": 100.0,
                "data_vencimento": "2026-06-01",
                "aluno_planos": {
                    "planos": {"nome": "Musculação"},
                    "alunos": {
                        "profile_id": "profile-uuid",
                        "profiles": {"nome": "Carlos"},
                    },
                },
            }]
        )

        job_notificar_atrasadas()
        mock_email.assert_called_once()
        args = mock_email.call_args[0]
        assert args[0] == "aluno@test.com"
        assert "atraso" in args[1].lower()


def test_job_sem_profile_id_nao_envia():
    with patch("app.notificacoes.jobs.supabase") as mock_supa, \
         patch("app.notificacoes.jobs._config_notificacoes", return_value=_CONFIG_ATIVA), \
         patch("app.notificacoes.jobs.enviar_email") as mock_email:

        mock_supa.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                "valor": 100.0,
                "data_vencimento": "2026-06-01",
                "aluno_planos": {
                    "planos": {"nome": "Musculação"},
                    "alunos": {"profile_id": None, "profiles": {"nome": "Carlos"}},
                },
            }]
        )

        job_notificar_atrasadas()
        mock_email.assert_not_called()
