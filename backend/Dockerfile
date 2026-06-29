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

# Pacotes Python do builder (sem gcc, sem cache de pip).
COPY --from=builder /root/.local /root/.local

# Código da aplicação (sem testes, sem migrations, sem scripts).
COPY app/ ./app/
COPY run.py gunicorn.conf.py ./

ENV PATH=/root/.local/bin:$PATH \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Usuário sem privilégios (evita que um exploit ganhe root no container).
RUN adduser -D appuser
USER appuser

EXPOSE 5000

# gunicorn lê WEB_CONCURRENCY, BIND e preload_app do gunicorn.conf.py.
# post_fork reinicia o cliente Supabase em cada worker (pool de conexões limpo).
# Usa 'python -m gunicorn' para evitar permission denied ao executar /root/.local/bin/gunicorn.
CMD ["python", "-m", "gunicorn", "-c", "gunicorn.conf.py", "run:app"]
