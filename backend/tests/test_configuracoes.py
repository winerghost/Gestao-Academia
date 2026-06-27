import io
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image

from app import create_app

_UID = "00000000-0000-0000-0000-000000000009"


def _png_bytes():
    buf = io.BytesIO()
    Image.new("RGB", (30, 20), (12, 34, 56)).save(buf, format="PNG")
    return buf.getvalue()


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


# ── GET /configuracoes/academia ──────────────────────────────────────────────

def test_obter_academia_autenticado(client):
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")
        mock_supa.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"id": 1, "nome": "Academia Teste", "notif_dias_antes": 1}
        )
        res = client.get("/configuracoes/academia", headers=_auth_headers())
        assert res.status_code == 200
        assert res.get_json()["nome"] == "Academia Teste"


def test_obter_academia_sem_token(client):
    res = client.get("/configuracoes/academia")
    assert res.status_code == 401


# ── PUT /configuracoes/academia ──────────────────────────────────────────────

def test_atualizar_academia_nao_admin(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")
        res = client.put("/configuracoes/academia",
                         json={"nome": "Nova"}, headers=_auth_headers())
        assert res.status_code == 403


def test_atualizar_academia_horario_invalido(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        res = client.put("/configuracoes/academia", json={
            "horarios": {"seg": {"abre": "25:00", "fecha": "22:00"}}
        }, headers=_auth_headers())
        assert res.status_code == 422


def test_atualizar_academia_email_invalido(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        res = client.put("/configuracoes/academia",
                         json={"email": "nao-eh-email"}, headers=_auth_headers())
        assert res.status_code == 422


def test_atualizar_academia_dias_antes_fora_do_limite(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        res = client.put("/configuracoes/academia",
                         json={"notif_dias_antes": 99}, headers=_auth_headers())
        assert res.status_code == 422


def test_atualizar_academia_sucesso(client):
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        mock_supa.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": 1, "nome": "Minha Academia", "notif_dias_antes": 3}]
        )
        res = client.put("/configuracoes/academia", json={
            "nome": "Minha Academia",
            "notif_dias_antes": 3,
            "horarios": {"seg": {"abre": "06:00", "fecha": "22:00", "fechado": False}},
        }, headers=_auth_headers())
        assert res.status_code == 200
        assert res.get_json()["nome"] == "Minha Academia"


def test_atualizar_academia_corpo_vazio(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        res = client.put("/configuracoes/academia", json={}, headers=_auth_headers())
        assert res.status_code == 400


# ── PUT /auth/me ─────────────────────────────────────────────────────────────

def test_atualizar_me_sucesso(client):
    with patch("app.auth.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "user-uuid", "nome": "Novo Nome", "telefone": "11999999999"}]
        )
        res = client.put("/auth/me",
                         json={"nome": "Novo Nome", "telefone": "11999999999"},
                         headers=_auth_headers())
        assert res.status_code == 200
        assert res.get_json()["nome"] == "Novo Nome"


def test_atualizar_me_preferencias_cor_invalida(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.put("/auth/me",
                         json={"preferencias": {"cor_destaque": "azul"}},
                         headers=_auth_headers())
        assert res.status_code == 422


def test_atualizar_me_corpo_vazio(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.put("/auth/me", json={}, headers=_auth_headers())
        assert res.status_code == 400


# ── POST /auth/change-password ───────────────────────────────────────────────

def test_trocar_senha_validacao(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.post("/auth/change-password",
                          json={"senha_atual": "atual", "senha_nova": "123"},
                          headers=_auth_headers())
        assert res.status_code == 422
        assert "senha_nova" in res.get_json()["fields"]


def test_trocar_senha_atual_incorreta(client):
    from gotrue.errors import AuthApiError
    with patch("app.auth.routes.supabase") as mock_supa, \
         patch("app.auth.routes.get_anon_client") as mock_factory, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.auth.admin.get_user_by_id.return_value = MagicMock(
            user=MagicMock(email="user@academia.com")
        )
        anon = MagicMock()
        anon.auth.sign_in_with_password.side_effect = AuthApiError("bad", 400, {})
        mock_factory.return_value = anon
        res = client.post("/auth/change-password",
                          json={"senha_atual": "errada", "senha_nova": "novaSenha1"},
                          headers=_auth_headers())
        assert res.status_code == 400
        assert "incorreta" in res.get_json()["error"].lower()


def test_trocar_senha_sucesso(client):
    with patch("app.auth.routes.supabase") as mock_supa, \
         patch("app.auth.routes.get_anon_client") as mock_factory, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.auth.admin.get_user_by_id.return_value = MagicMock(
            user=MagicMock(email="user@academia.com")
        )
        mock_factory.return_value = MagicMock()  # login revalida com sucesso
        res = client.post("/auth/change-password",
                          json={"senha_atual": "atualSenha1", "senha_nova": "novaSenha1"},
                          headers=_auth_headers())
        assert res.status_code == 200
        mock_supa.auth.admin.update_user_by_id.assert_called_once()


# ── GET /configuracoes/usuarios ──────────────────────────────────────────────

def test_listar_usuarios_admin(client):
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        prof = {
            "id": "u1", "nome": "Ana", "tipo": "aluno",
            "telefone": None, "ativo": True, "created_at": "2024-01-01",
        }
        mock_supa.table.return_value.select.return_value.order.return_value.execute.return_value = MagicMock(
            data=[prof]
        )
        auth_user = MagicMock()
        auth_user.id = "u1"
        auth_user.email = "ana@academia.com"
        mock_supa.auth.admin.list_users.return_value = [auth_user]

        res = client.get("/configuracoes/usuarios", headers=_auth_headers())
        assert res.status_code == 200
        body = res.get_json()
        assert len(body) == 1
        assert body[0]["email"] == "ana@academia.com"
        assert body[0]["tipo"] == "aluno"
        assert body[0]["ativo"] is True


def test_listar_usuarios_nao_admin(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")
        res = client.get("/configuracoes/usuarios", headers=_auth_headers())
        assert res.status_code == 403


def test_listar_usuarios_sem_token(client):
    res = client.get("/configuracoes/usuarios")
    assert res.status_code == 401


# ── PATCH /configuracoes/usuarios/<id>/tipo ──────────────────────────────────

def test_alterar_tipo_sucesso(client):
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        mock_supa.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "u1", "tipo": "instrutor"}]
        )
        res = client.patch("/configuracoes/usuarios/u1/tipo",
                           json={"tipo": "instrutor"}, headers=_auth_headers())
        assert res.status_code == 200
        assert res.get_json()["tipo"] == "instrutor"


def test_alterar_tipo_para_instrutor_cria_registro_instrutores(client):
    """Ao promover para instrutor, insere linha na tabela instrutores quando não existe."""
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")

        profiles_tbl = MagicMock()
        profiles_tbl.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "u2", "tipo": "instrutor"}]
        )

        instrutores_tbl = MagicMock()
        instrutores_tbl.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None   # nenhum registro existente
        )

        mock_supa.table.side_effect = lambda name: profiles_tbl if name == "profiles" else instrutores_tbl

        res = client.patch("/configuracoes/usuarios/u2/tipo",
                           json={"tipo": "instrutor"}, headers=_auth_headers())
        assert res.status_code == 200
        instrutores_tbl.insert.assert_called_once_with({"profile_id": "u2"})


def test_alterar_tipo_para_instrutor_nao_duplica_registro(client):
    """Se já existe linha em instrutores, não deve inserir duplicata."""
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")

        profiles_tbl = MagicMock()
        profiles_tbl.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "u3", "tipo": "instrutor"}]
        )

        instrutores_tbl = MagicMock()
        instrutores_tbl.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": "inst-uuid"}   # registro já existe
        )

        mock_supa.table.side_effect = lambda name: profiles_tbl if name == "profiles" else instrutores_tbl

        res = client.patch("/configuracoes/usuarios/u3/tipo",
                           json={"tipo": "instrutor"}, headers=_auth_headers())
        assert res.status_code == 200
        instrutores_tbl.insert.assert_not_called()


def test_alterar_tipo_proprio_bloqueado(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        # user-uuid é o próprio usuário logado (ver _mock_auth)
        res = client.patch("/configuracoes/usuarios/user-uuid/tipo",
                           json={"tipo": "aluno"}, headers=_auth_headers())
        assert res.status_code == 400


def test_alterar_tipo_invalido(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        res = client.patch("/configuracoes/usuarios/u1/tipo",
                           json={"tipo": "superadmin"}, headers=_auth_headers())
        assert res.status_code == 422


def test_alterar_tipo_nao_admin(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="instrutor")
        res = client.patch("/configuracoes/usuarios/u1/tipo",
                           json={"tipo": "admin"}, headers=_auth_headers())
        assert res.status_code == 403


def test_alterar_tipo_usuario_inexistente(client):
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        mock_supa.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        res = client.patch("/configuracoes/usuarios/u1/tipo",
                           json={"tipo": "aluno"}, headers=_auth_headers())
        assert res.status_code == 404


# ── PATCH /configuracoes/usuarios/<id>/status ────────────────────────────────

def test_alterar_status_sucesso(client):
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        mock_supa.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "u1", "ativo": False}]
        )
        res = client.patch("/configuracoes/usuarios/u1/status",
                           json={"ativo": False}, headers=_auth_headers())
        assert res.status_code == 200
        assert res.get_json()["ativo"] is False


def test_alterar_status_proprio_bloqueado(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        res = client.patch("/configuracoes/usuarios/user-uuid/status",
                           json={"ativo": False}, headers=_auth_headers())
        assert res.status_code == 400


def test_alterar_status_corpo_invalido(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        res = client.patch("/configuracoes/usuarios/u1/status",
                           json={}, headers=_auth_headers())
        assert res.status_code == 422


def test_alterar_status_nao_admin(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")
        res = client.patch("/configuracoes/usuarios/u1/status",
                           json={"ativo": False}, headers=_auth_headers())
        assert res.status_code == 403


def test_alterar_status_usuario_inexistente(client):
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        mock_supa.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        res = client.patch("/configuracoes/usuarios/u1/status",
                           json={"ativo": True}, headers=_auth_headers())
        assert res.status_code == 404


# ── Enforcement: conta desativada perde acesso ───────────────────────────────

def test_usuario_desativado_bloqueado_no_middleware(client):
    """Token válido, mas profile.ativo = False → 403 em qualquer rota."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="aluno", ativo=False)
        res = client.get("/auth/me", headers=_auth_headers())
        assert res.status_code == 403
        assert "desativada" in res.get_json()["error"].lower()


def test_login_conta_desativada_bloqueado(client):
    with patch("app.auth.routes.supabase") as mock_supa, \
         patch("app.auth.routes.get_anon_client") as mock_factory:
        anon = MagicMock()
        anon.auth.sign_in_with_password.return_value = MagicMock(
            session=MagicMock(access_token="at", refresh_token="rt"),
            user=MagicMock(id="u1", email="a@academia.com"),
        )
        mock_factory.return_value = anon
        mock_supa.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"ativo": False}
        )
        res = client.post("/auth/login",
                          json={"email": "a@academia.com", "password": "secret"})
        assert res.status_code == 403
        assert "desativada" in res.get_json()["error"].lower()


def test_login_conta_ativa_sucesso(client):
    with patch("app.auth.routes.supabase") as mock_supa, \
         patch("app.auth.routes.get_anon_client") as mock_factory:
        anon = MagicMock()
        anon.auth.sign_in_with_password.return_value = MagicMock(
            session=MagicMock(access_token="at", refresh_token="rt"),
            user=MagicMock(id="u1", email="a@academia.com"),
        )
        mock_factory.return_value = anon
        mock_supa.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = MagicMock(
            data={"ativo": True}
        )
        res = client.post("/auth/login",
                          json={"email": "a@academia.com", "password": "secret"})
        assert res.status_code == 200
        assert res.get_json()["access_token"] == "at"


# ── Avatar de usuário (admin/recepcionista alteram a foto de outro) ───────────

def _mock_profile_existe(mock_supa, existe=True):
    mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
        data={"id": _UID} if existe else None
    )


def test_definir_avatar_usuario_admin(client):
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.configuracoes.routes.upload_avatar", return_value="https://cdn.fake/u/x.jpg") as mock_up, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        _mock_profile_existe(mock_supa, True)
        data = {"file": (io.BytesIO(_png_bytes()), "foto.png")}
        res = client.post(f"/configuracoes/usuarios/{_UID}/avatar", headers=_auth_headers(),
                          data=data, content_type="multipart/form-data")
        assert res.status_code == 200
        assert res.get_json()["avatar_url"] == "https://cdn.fake/u/x.jpg"
        mock_up.assert_called_once()


def test_definir_avatar_usuario_recepcionista(client):
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.configuracoes.routes.upload_avatar", return_value="https://cdn.fake/u/y.jpg"), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")
        _mock_profile_existe(mock_supa, True)
        data = {"file": (io.BytesIO(_png_bytes()), "foto.png")}
        res = client.post(f"/configuracoes/usuarios/{_UID}/avatar", headers=_auth_headers(),
                          data=data, content_type="multipart/form-data")
        assert res.status_code == 200


def test_definir_avatar_usuario_instrutor_negado(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="instrutor")
        data = {"file": (io.BytesIO(_png_bytes()), "foto.png")}
        res = client.post(f"/configuracoes/usuarios/{_UID}/avatar", headers=_auth_headers(),
                          data=data, content_type="multipart/form-data")
        assert res.status_code == 403


def test_definir_avatar_usuario_inexistente_404(client):
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        _mock_profile_existe(mock_supa, False)
        data = {"file": (io.BytesIO(_png_bytes()), "foto.png")}
        res = client.post(f"/configuracoes/usuarios/{_UID}/avatar", headers=_auth_headers(),
                          data=data, content_type="multipart/form-data")
        assert res.status_code == 404


def test_definir_avatar_usuario_sem_arquivo_400(client):
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        _mock_profile_existe(mock_supa, True)
        res = client.post(f"/configuracoes/usuarios/{_UID}/avatar", headers=_auth_headers())
        assert res.status_code == 400


def test_remover_avatar_usuario_admin(client):
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.configuracoes.routes.remover_avatares_storage") as mock_rm, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        _mock_profile_existe(mock_supa, True)
        res = client.delete(f"/configuracoes/usuarios/{_UID}/avatar", headers=_auth_headers())
        assert res.status_code == 200
        assert res.get_json()["avatar_url"] is None
        mock_rm.assert_called_once()


def test_remover_avatar_usuario_instrutor_negado(client):
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="instrutor")
        res = client.delete(f"/configuracoes/usuarios/{_UID}/avatar", headers=_auth_headers())
        assert res.status_code == 403
