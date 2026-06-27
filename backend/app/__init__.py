import os
from flask import Flask, jsonify
from flask_cors import CORS
from .config import Config
from .extensions import limiter
from .auth import auth_bp
from .alunos import alunos_bp
from .instrutores import instrutores_bp
from .planos import planos_bp
from .mensalidades import mensalidades_bp
from .dashboard import dashboard_bp
from .relatorios import relatorios_bp
from .portal import portal_bp
from .avaliacoes import avaliacoes_bp
from .configuracoes import configuracoes_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Limite global do corpo da requisição: barra uploads absurdos antes mesmo
    # de lê-los na memória. Folga sobre AVATAR_MAX_BYTES p/ overhead do
    # multipart; os endpoints JSON têm corpos minúsculos, então não os afeta.
    app.config["MAX_CONTENT_LENGTH"] = Config.AVATAR_MAX_BYTES + 1024 * 1024

    # Em testes (pytest) não falhamos por env ausente nem ativamos o rate
    # limit / scheduler — mantém a suíte determinística e offline.
    testing = bool(os.environ.get("PYTEST_CURRENT_TEST")) or app.config.get("TESTING")

    # Fail-fast: sem as chaves do Supabase o backend não sobe (evita rodar
    # meio-configurado e vazar erros estranhos em runtime).
    faltando = Config.missing_required()
    if faltando and not testing:
        raise RuntimeError(
            "Variáveis de ambiente obrigatórias ausentes: " + ", ".join(faltando)
        )

    # CORS restritivo: apenas as origens explícitas do Next.js (sem wildcard).
    # Em produção, defina ALLOWED_ORIGINS no .env.
    CORS(
        app,
        origins=Config.ALLOWED_ORIGINS,
        supports_credentials=True,
        expose_headers=["Content-Disposition"],
        allow_headers=["Authorization", "Content-Type"],
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    )

    # Rate limiting (limites e storage vêm de app.config / RATELIMIT_*).
    app.config["RATELIMIT_ENABLED"] = not testing
    limiter.init_app(app)

    @app.errorhandler(413)
    def _payload_grande(_e):
        return jsonify({
            "error": "Arquivo grande demais. Envie uma imagem de até 4 MB."
        }), 413

    @app.errorhandler(429)
    def _rate_limit_excedido(_e):
        return jsonify({
            "error": "Muitas requisições em pouco tempo. Aguarde e tente de novo."
        }), 429

    @app.errorhandler(500)
    def _erro_interno(e):
        app.logger.exception("Erro interno não tratado")
        return jsonify({"error": "Erro interno do servidor", "detalhe": str(e)}), 500

    app.register_blueprint(auth_bp)
    app.register_blueprint(alunos_bp)
    app.register_blueprint(instrutores_bp)
    app.register_blueprint(planos_bp)
    app.register_blueprint(mensalidades_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(relatorios_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(avaliacoes_bp)
    app.register_blueprint(configuracoes_bp)

    if not testing:
        from .mensalidades.jobs import iniciar_scheduler
        iniciar_scheduler()

    return app
