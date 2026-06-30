# ── Stage 1: builder ──────────────────────────────────────────────────────────
# Instala as dependências Python num ambiente isolado.
# gcc + musl-dev: compilam extensões C (ex.: cryptography usado pelo supabase).
# jpeg-dev + zlib-dev: Pillow precisa das libs de sistema para processar imagens.
FROM python:3.11-alpine AS builder
WORKDIR /build

RUN apk add --no-cache gcc musl-dev libffi-dev jpeg-dev zlib-dev

COPY requirements.txt .
# --user: instala em /root/.local (copiado para o stage final sem gcc).
# --no-cache-dir: não acumula cache de pip na imagem.
RUN pip install --user --no-cache-dir -r requirements.txt

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
# Imagem mínima de produção: apenas runtime libs, sem compiladores.
FROM python:3.11-alpine
WORKDIR /app

# Shared libs de runtime que Pillow e libffi precisam em tempo de execução.
RUN apk add --no-cache jpeg zlib libffi

# Usuário sem privilégios (evita que um exploit ganhe root no container).
# Criado ANTES de copiar os pacotes para podermos defini-lo como dono.
RUN adduser -D appuser

# Pacotes Python do builder (sem gcc, sem cache de pip).
# Vão para a HOME do appuser, não /root/.local: no Alpine /root é 0700 e o
# appuser não consegue atravessá-lo → "No module named gunicorn". Em
# /home/appuser/.local o Python encontra o user-site automaticamente (HOME).
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Código da aplicação (sem testes, sem migrations, sem scripts).
COPY --chown=appuser:appuser app/ ./app/
COPY --chown=appuser:appuser run.py gunicorn.conf.py ./

# HOME explícito: o Docker USER não define $HOME, e o Python deriva o user-site
# (~/.local/lib/...) a partir dele. Sem isso, voltaria a procurar em /root/.local.
ENV HOME=/home/appuser \
    PATH=/home/appuser/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER appuser

EXPOSE 5000

# gunicorn lê WEB_CONCURRENCY, BIND e preload_app do gunicorn.conf.py.
# post_fork reinicia o cliente Supabase em cada worker (pool de conexões limpo).
CMD ["python", "-m", "gunicorn", "-c", "gunicorn.conf.py", "run:app"]
