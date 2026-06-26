from flask import Flask
from flask_cors import CORS
from .config import Config
from .auth import auth_bp
from .alunos import alunos_bp
from .instrutores import instrutores_bp
from .planos import planos_bp
from .mensalidades import mensalidades_bp
from .dashboard import dashboard_bp
from .relatorios import relatorios_bp
from .portal import portal_bp
from .avaliacoes import avaliacoes_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(app, origins=["http://localhost:3000"], expose_headers=["Content-Disposition"])

    app.register_blueprint(auth_bp)
    app.register_blueprint(alunos_bp)
    app.register_blueprint(instrutores_bp)
    app.register_blueprint(planos_bp)
    app.register_blueprint(mensalidades_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(relatorios_bp)
    app.register_blueprint(portal_bp)
    app.register_blueprint(avaliacoes_bp)

    if not app.config.get("TESTING"):
        from .mensalidades.jobs import iniciar_scheduler
        iniciar_scheduler()

    return app
