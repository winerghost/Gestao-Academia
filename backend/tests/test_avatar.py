import io
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image

from app import create_app
from app.auth.avatar import processar_imagem, url_gravatar, AvatarError


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _auth_headers():
    return {"Authorization": "Bearer token-fake"}


def _mock_auth(mock_supa, tipo="admin", ativo=True):
    user = MagicMock()
    user.id = "user-uuid"
    mock_supa.auth.get_user.return_value = MagicMock(user=user)
    mock_supa.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
        data={"tipo": tipo, "ativo": ativo}
    )


def _png_bytes(size=(40, 20), color=(200, 30, 30)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


# ── Processamento de imagem (unit) ───────────────────────────────────────────

def test_processar_imagem_reencoda_para_jpeg_quadrado():
    saida = processar_imagem(_png_bytes(size=(40, 20)))
    img = Image.open(io.BytesIO(saida))
    assert img.format == "JPEG"
    assert img.size == (512, 512)  # AVATAR_SIZE_PX padrão, recortado quadrado


def test_processar_imagem_rejeita_lixo():
    with pytest.raises(AvatarError):
        processar_imagem(b"isto nao e uma imagem")


def test_processar_imagem_rejeita_vazio():
    with pytest.raises(AvatarError):
        processar_imagem(b"")


def test_url_gravatar_usa_hash_sha256_minusculo():
    # SHA-256 de "user@academia.com" (e-mail normalizado).
    import hashlib
    h = hashlib.sha256("user@academia.com".encode()).hexdigest()
    url = url_gravatar("  User@Academia.com  ")
    assert h in url
    assert "d=404" in url


# ── POST /auth/me/avatar ─────────────────────────────────────────────────────

def test_upload_avatar_sem_token(client):
    res = client.post("/auth/me/avatar")
    assert res.status_code == 401


def test_upload_avatar_sem_arquivo(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.post("/auth/me/avatar", headers=_auth_headers())
        assert res.status_code == 400


def test_upload_avatar_tipo_invalido(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        data = {"file": (io.BytesIO(b"arquivo de texto"), "doc.txt")}
        res = client.post("/auth/me/avatar", headers=_auth_headers(),
                          data=data, content_type="multipart/form-data")
        assert res.status_code == 400


def test_upload_avatar_sucesso(client):
    with patch("app.auth.routes.supabase") as mock_supa, \
         patch("app.auth.routes.upload_avatar") as mock_upload, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_upload.return_value = "https://cdn.fake/avatars/user-uuid/abc.jpg"
        data = {"file": (io.BytesIO(_png_bytes()), "foto.png")}
        res = client.post("/auth/me/avatar", headers=_auth_headers(),
                          data=data, content_type="multipart/form-data")
        assert res.status_code == 200
        assert res.get_json()["avatar_url"].endswith("abc.jpg")
        mock_upload.assert_called_once()
        mock_supa.table.return_value.update.assert_called_once_with(
            {"avatar_url": "https://cdn.fake/avatars/user-uuid/abc.jpg"}
        )


def test_upload_avatar_falha_storage_retorna_502(client):
    with patch("app.auth.routes.supabase"), \
         patch("app.auth.routes.upload_avatar", side_effect=RuntimeError("boom")), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        data = {"file": (io.BytesIO(_png_bytes()), "foto.png")}
        res = client.post("/auth/me/avatar", headers=_auth_headers(),
                          data=data, content_type="multipart/form-data")
        assert res.status_code == 502


# ── DELETE /auth/me/avatar ───────────────────────────────────────────────────

def test_remover_avatar_sucesso(client):
    with patch("app.auth.routes.supabase") as mock_supa, \
         patch("app.auth.routes.remover_avatares_storage") as mock_rm, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.delete("/auth/me/avatar", headers=_auth_headers())
        assert res.status_code == 200
        assert res.get_json()["avatar_url"] is None
        mock_rm.assert_called_once()
        mock_supa.table.return_value.update.assert_called_once_with({"avatar_url": None})


# ── POST /auth/me/avatar/gravatar ────────────────────────────────────────────

def test_usar_gravatar_sucesso(client):
    with patch("app.auth.routes.supabase") as mock_supa, \
         patch("app.auth.routes.gravatar_existe", return_value=True), \
         patch("app.auth.routes.remover_avatares_storage"), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.auth.admin.get_user_by_id.return_value = MagicMock(
            user=MagicMock(email="user@academia.com")
        )
        res = client.post("/auth/me/avatar/gravatar", headers=_auth_headers())
        assert res.status_code == 200
        assert "gravatar.com/avatar/" in res.get_json()["avatar_url"]
        mock_supa.table.return_value.update.assert_called_once()


def test_usar_gravatar_inexistente(client):
    with patch("app.auth.routes.supabase") as mock_supa, \
         patch("app.auth.routes.gravatar_existe", return_value=False), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.auth.admin.get_user_by_id.return_value = MagicMock(
            user=MagicMock(email="user@academia.com")
        )
        res = client.post("/auth/me/avatar/gravatar", headers=_auth_headers())
        assert res.status_code == 404
        mock_supa.table.return_value.update.assert_not_called()
