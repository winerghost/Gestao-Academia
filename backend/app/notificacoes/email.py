import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from ..config import Config

logger = logging.getLogger(__name__)


def enviar_email(destinatario: str, assunto: str, corpo_html: str) -> bool:
    """Envia e-mail via Gmail SMTP. Retorna True se enviado com sucesso."""
    if not all([Config.EMAIL_USER, Config.EMAIL_PASSWORD, Config.EMAIL_FROM]):
        logger.warning("Credenciais de e-mail não configuradas — e-mail não enviado.")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = assunto
    msg["From"] = Config.EMAIL_FROM
    msg["To"] = destinatario
    msg.attach(MIMEText(corpo_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(Config.EMAIL_HOST, Config.EMAIL_PORT, timeout=10) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.login(Config.EMAIL_USER, Config.EMAIL_PASSWORD)
            smtp.sendmail(Config.EMAIL_FROM, destinatario, msg.as_string())
        logger.info("E-mail enviado para %s — %s", destinatario, assunto)
        return True
    except Exception:
        logger.exception("Falha ao enviar e-mail para %s", destinatario)
        return False


# ── Templates HTML ────────────────────────────────────────────────────────────

def _base(titulo: str, conteudo: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head><meta charset="UTF-8"></head>
    <body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr><td align="center" style="padding:32px 16px;">
          <table width="560" style="background:#fff;border-radius:8px;overflow:hidden;
                 box-shadow:0 1px 4px rgba(0,0,0,.08);">
            <tr>
              <td style="background:#1a56db;padding:24px 32px;">
                <h1 style="margin:0;color:#fff;font-size:20px;">🏋️ Gestão Academia</h1>
              </td>
            </tr>
            <tr>
              <td style="padding:32px;">
                <h2 style="margin:0 0 16px;color:#111827;font-size:18px;">{titulo}</h2>
                {conteudo}
                <p style="margin:24px 0 0;color:#6b7280;font-size:12px;">
                  Este é um e-mail automático. Não responda.
                </p>
              </td>
            </tr>
          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """


def template_vencimento(nome: str, plano: str, data_vcto: str, valor: float) -> str:
    conteudo = f"""
    <p style="color:#374151;">Olá, <strong>{nome}</strong>!</p>
    <p style="color:#374151;">Sua mensalidade do plano <strong>{plano}</strong>
       vence <strong>amanhã, {data_vcto}</strong>.</p>
    <table style="background:#f9fafb;border-radius:6px;padding:16px;width:100%;
                  border-collapse:collapse;margin:16px 0;">
      <tr>
        <td style="color:#6b7280;padding:4px 0;">Plano</td>
        <td style="color:#111827;font-weight:bold;text-align:right;">{plano}</td>
      </tr>
      <tr>
        <td style="color:#6b7280;padding:4px 0;">Vencimento</td>
        <td style="color:#111827;font-weight:bold;text-align:right;">{data_vcto}</td>
      </tr>
      <tr>
        <td style="color:#6b7280;padding:4px 0;">Valor</td>
        <td style="color:#111827;font-weight:bold;text-align:right;">R$ {valor:.2f}</td>
      </tr>
    </table>
    <p style="color:#374151;">
      Efetue o pagamento até a data de vencimento para evitar juros.
    </p>
    """
    return _base("Lembrete de vencimento", conteudo)


def template_atrasada(nome: str, plano: str, data_vcto: str, valor: float, dias: int) -> str:
    conteudo = f"""
    <p style="color:#374151;">Olá, <strong>{nome}</strong>!</p>
    <p style="color:#dc2626;">
      Sua mensalidade do plano <strong>{plano}</strong> está em atraso há
      <strong>{dias} dia(s)</strong>.
    </p>
    <table style="background:#fef2f2;border-radius:6px;padding:16px;width:100%;
                  border-collapse:collapse;margin:16px 0;">
      <tr>
        <td style="color:#6b7280;padding:4px 0;">Plano</td>
        <td style="color:#111827;font-weight:bold;text-align:right;">{plano}</td>
      </tr>
      <tr>
        <td style="color:#6b7280;padding:4px 0;">Vencimento</td>
        <td style="color:#dc2626;font-weight:bold;text-align:right;">{data_vcto}</td>
      </tr>
      <tr>
        <td style="color:#6b7280;padding:4px 0;">Valor original</td>
        <td style="color:#111827;font-weight:bold;text-align:right;">R$ {valor:.2f}</td>
      </tr>
      <tr>
        <td style="color:#6b7280;padding:4px 0;">Juros (2% a.m.)</td>
        <td style="color:#dc2626;font-weight:bold;text-align:right;">
          R$ {valor * 0.02 * (dias / 30):.2f}
        </td>
      </tr>
    </table>
    <p style="color:#374151;">
      Regularize sua situação o quanto antes para evitar o bloqueio do acesso.
    </p>
    """
    return _base("Mensalidade em atraso", conteudo)
