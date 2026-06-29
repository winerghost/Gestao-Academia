import os
from flask import Flask, jsonify, request
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

    # Aviso operacional: com "memory://" o limite NÃO é compartilhado entre
    # workers/instâncias — o controle de brute force no login fica enfraquecido.
    # Em produção, defina RATELIMIT_STORAGE_URI=redis://... (ver config.py).
    if not testing and str(Config.RATELIMIT_STORAGE_URI).startswith("memory://"):
        app.logger.warning(
            "Rate limit usando 'memory://' — não compartilhado entre workers. "
            "Defina RATELIMIT_STORAGE_URI (ex.: redis://...) em produção."
        )

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
        # O texto cru da exceção pode revelar schema/erros do PostgREST. Só
        # expomos esse detalhe em modo debug (dev); em produção, mensagem genérica.
        corpo = {"error": "Erro interno do servidor"}
        if app.debug:
            corpo["detalhe"] = str(e)
        return jsonify(corpo), 500

    @app.after_request
    def _cabecalhos_seguranca(resp):
        # Defesa em profundidade nas respostas da API (JSON e downloads):
        # - nosniff: impede o navegador de "adivinhar" o content-type.
        # - DENY/frame-ancestors: a API nunca deve ser embutida em <iframe>.
        # - CSP restritiva: a API não serve HTML executável; trava tudo.
        # - HSTS só faz sentido sob HTTPS (em http é ignorado pelo navegador).
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault(
            "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
        )
        if request.is_secure:
            resp.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return resp

    @app.get("/health")
    def health():
        # Endpoint público para healthcheck do Docker e monitoramento.
        # Retorna 200 quando a aplicação está pronta para receber requisições.
        return jsonify({"status": "ok"})

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
