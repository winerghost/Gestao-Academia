"""Lógica de foto de perfil: processamento de imagem, Storage e Gravatar.

Mantida fora de `routes.py` para isolar a regra de negócio (SOLID — uma
responsabilidade por módulo) e facilitar os testes.

Decisões de segurança:
- A imagem enviada NUNCA é gravada como veio. Ela é reaberta, validada e
  *re-encodada* com Pillow para JPEG. Isso descarta metadados EXIF e qualquer
  payload malicioso anexado a um "arquivo de imagem" (polyglots, etc.).
- O caminho no Storage é sempre "<user_id>/<arquivo>", então um usuário só
  escreve na própria pasta (casa com a RLS de storage.objects da migration 009).
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import io
import re
import uuid

import httpx
from PIL import Image, UnidentifiedImageError

from ..config import Config

# Formatos de entrada que aceitamos (a saída é sempre JPEG).
_FORMATOS_ACEITOS = {"JPEG", "PNG", "WEBP"}

# Data URL: "data:image/<tipo>;base64,<dados>"
_DATAURL_RE = re.compile(r"^data:image/[a-zA-Z0-9.+-]+;base64,(.*)$", re.DOTALL)


class AvatarError(Exception):
    """Erro de validação/processamento da imagem (vira 400 na rota)."""


def processar_imagem(raw: bytes) -> bytes:
    """Valida e re-encoda a imagem para um JPEG quadrado e leve.

    Levanta AvatarError se o conteúdo não for uma imagem suportada.
    """
    if not raw:
        raise AvatarError("Arquivo vazio.")
    if len(raw) > Config.AVATAR_MAX_BYTES:
        raise AvatarError("Arquivo grande demais. Envie uma imagem de até 4 MB.")

    try:
        img = Image.open(io.BytesIO(raw))
        img.load()  # força a leitura real dos pixels (pega arquivos corrompidos)
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise AvatarError("Arquivo inválido. Envie uma imagem JPG, PNG ou WEBP.")

    if img.format not in _FORMATOS_ACEITOS:
        raise AvatarError("Formato não suportado. Use JPG, PNG ou WEBP.")

    # A partir daqui qualquer erro de processamento vira AvatarError (HTTP 400),
    # nunca um 500: uma imagem maliciosa/inesperada não pode derrubar a rota.
    try:
        # Achata transparência sobre fundo branco e normaliza para RGB.
        if img.mode in ("RGBA", "LA", "P"):
            fundo = Image.new("RGB", img.size, (255, 255, 255))
            img = img.convert("RGBA")
            fundo.paste(img, mask=img.split()[-1])
            img = fundo
        else:
            img = img.convert("RGB")

        img = _recorte_quadrado(img)
        lado = Config.AVATAR_SIZE_PX
        img = img.resize((lado, lado), Image.LANCZOS)

        saida = io.BytesIO()
        img.save(saida, format="JPEG", quality=85, optimize=True)
        return saida.getvalue()
    except AvatarError:
        raise
    except Exception:  # noqa: BLE001 — converte qualquer falha de imagem em 400
        raise AvatarError("Não foi possível processar a imagem. Tente outra.")


def processar_imagem_base64(data_url: str) -> bytes:
    """Decodifica um data URL base64 e processa como imagem (ver processar_imagem).

    Usado quando a foto chega embutida em JSON (ex.: captura por webcam no
    cadastro de aluno). O Pillow continua sendo a validação real do conteúdo.
    """
    m = _DATAURL_RE.match(data_url or "")
    if not m:
        raise AvatarError("Foto inválida (esperado data URL base64).")
    try:
        raw = base64.b64decode(m.group(1).strip())
    except (ValueError, binascii.Error):
        raise AvatarError("Foto inválida (base64 corrompido).")
    return processar_imagem(raw)


def _recorte_quadrado(img: Image.Image) -> Image.Image:
    """Recorta centralizado para um quadrado (evita distorcer no resize)."""
    largura, altura = img.size
    if largura == altura:
        return img
    lado = min(largura, altura)
    esq = (largura - lado) // 2
    topo = (altura - lado) // 2
    return img.crop((esq, topo, esq + lado, topo + lado))


# ── Supabase Storage ─────────────────────────────────────────────────────────

def _bucket(supabase):
    return supabase.storage.from_(Config.AVATAR_BUCKET)


def _listar_arquivos(supabase, user_id: str) -> list[str]:
    """Nomes dos arquivos na pasta do usuário (sem o prefixo da pasta)."""
    itens = _bucket(supabase).list(user_id) or []
    return [it["name"] for it in itens if it.get("name")]


def remover_avatares_storage(supabase, user_id: str) -> None:
    """Apaga todos os arquivos da pasta do usuário (idempotente)."""
    nomes = _listar_arquivos(supabase, user_id)
    if nomes:
        _bucket(supabase).remove([f"{user_id}/{n}" for n in nomes])


def upload_avatar(supabase, user_id: str, jpeg_bytes: bytes) -> str:
    """Sobe a foto processada e retorna a URL pública (com cache-bust).

    Usa nome único por upload para furar o cache do CDN, depois apaga as
    versões antigas. Sobe a nova ANTES de apagar as antigas: se o upload
    falhar, a foto atual continua intacta.
    """
    antigos = _listar_arquivos(supabase, user_id)

    caminho = f"{user_id}/{uuid.uuid4().hex}.jpg"
    _bucket(supabase).upload(
        caminho,
        jpeg_bytes,
        {"content-type": "image/jpeg", "cache-control": "3600", "upsert": "false"},
    )

    if antigos:
        _bucket(supabase).remove([f"{user_id}/{n}" for n in antigos])

    return _bucket(supabase).get_public_url(caminho)


# ── Gravatar ─────────────────────────────────────────────────────────────────

def _gravatar_hash(email: str) -> str:
    # Gravatar: e-mail em minúsculas e sem espaços nas pontas, hash SHA-256.
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


def url_gravatar(email: str) -> str:
    """URL do Gravatar do e-mail. d=404 → 404 quando não há foto cadastrada,
    o que o frontend usa para cair de volta nas iniciais via onError."""
    h = _gravatar_hash(email)
    lado = Config.AVATAR_SIZE_PX
    return f"https://gravatar.com/avatar/{h}?s={lado}&d=404"


def gravatar_existe(email: str) -> bool:
    """Confere se o e-mail tem foto no Gravatar (GET com d=404)."""
    try:
        resp = httpx.get(url_gravatar(email), timeout=5.0)
        return resp.status_code == 200
    except httpx.HTTPError:
        return False
