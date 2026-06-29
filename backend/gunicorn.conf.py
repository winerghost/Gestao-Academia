"""Configuração do gunicorn para produção.

preload_app=True: carrega a aplicação UMA vez no processo master antes de fazer
fork dos workers. O APScheduler (iniciado em create_app) roda somente no master;
threads não sobrevivem ao fork(), então os workers não ganham cópias do scheduler
— evita que N workers disparem N e-mails por job (achado N-1).

post_fork: reinicializa o cliente httpx do Supabase em cada worker. Conexões
herdadas via fork podem estar em estado inconsistente; recriar o transporte
garante que cada worker tenha seu próprio pool de conexões limpo.

M-1 (rate limit): configure RATELIMIT_STORAGE_URI=redis://... no .env de produção.
"""
import os


preload_app = True

workers = int(os.environ.get("WEB_CONCURRENCY", 2))
bind = os.environ.get("BIND", "0.0.0.0:5000")
worker_class = "sync"
timeout = 30
accesslog = "-"
errorlog = "-"


def post_fork(server, worker):
    from app.supabase_client import supabase, _harden_session
    _harden_session(supabase)
