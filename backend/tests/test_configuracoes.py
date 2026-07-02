"""Testes de configurações: usuários, academia e avatar.

Conceitos testados:
  UUID nos path params (N-3)
    Rotas com `<uuid:user_id>` rejeitam automaticamente valores não-UUID.
    Flask faz essa validação no roteamento antes mesmo de chamar o handler.
    Por isso TODOS os testes de rota /configuracoes/usuarios/<id>/... usam
    constantes UUID válidas (ex.: "00000000-0000-0000-0000-000000000001").

  Regras de admin — proteção de integridade do sistema:
    - Nenhum admin pode excluir/desativar/mudar o próprio tipo (self-guard).
    - O último admin não pode ser excluído (sistema ficaria sem admin).
    - Aluno com mensalidades atrasadas não pode ser desativado nem excluído
      até quitar os débitos (integridade financeira).
    - Aluno com histórico financeiro não pode ser excluído (preservação contábil).

  Mass assignment / escalonamento de privilégio
    CriarUsuarioSchema bloqueia tipo='aluno' — alunos têm fluxo próprio (CPF obrigatório).
    ProfileUpdateSchema bloqueia 'tipo' e 'ativo' no /auth/me.

  Avatar de usuário (admin/recepcionista editam foto de outro)
    Mesmo pipeline de sanitização do avatar próprio: Pillow re-encoda.
    Instrutor não tem permissão para alterar foto de outros.

  Conta desativada (profiles.ativo = False)
    O middleware verifica `ativo` em TODA requisição autenticada.
    Uma conta desativada recebe 403 mesmo com token JWT válido.

Padrão de mock (constantes UUID):
  Cada papel/entidade tem seu próprio UUID fixo para evitar colisões entre
  mocks e para que o `g.user_id == uid` (self-guard) funcione corretamente.
  _UID_SELF é o usuário logado (definido em _mock_auth como user.id).
"""
import io
from unittest.mock import patch, MagicMock

from PIL import Image

from tests._helpers import mock_auth, auth_headers as _auth_headers

# ── Constantes UUID ────────────────────────────────────────────────────────────
# UUID válidos para path params. Flask <uuid:...> rejeita strings não-UUID.

_UID      = "00000000-0000-0000-0000-000000000009"  # id genérico p/ avatar
_UID1     = "00000000-0000-0000-0000-000000000001"  # usuário 1 (alvo de testes)
_UID2     = "00000000-0000-0000-0000-000000000002"  # usuário 2
_UID3     = "00000000-0000-0000-0000-000000000003"  # usuário 3
_UID_SELF  = "00000000-0000-0000-0000-000000000099"  # usuário logado nos testes
_UID_OTHER = "00000000-0000-0000-0000-000000000011"  # outro admin (alvo de exclusão)
_UID_UNICO = "00000000-0000-0000-0000-000000000022"  # único admin no sistema
_UID_ALUNO = "00000000-0000-0000-0000-000000000033"  # aluno nas regras de negócio
_UID_ANON  = "00000000-0000-0000-0000-000000000044"  # usuário sem permissão


def _png_bytes():
    """Gera bytes de PNG válido para testes de upload de avatar."""
    buf = io.BytesIO()
    Image.new("RGB", (30, 20), (12, 34, 56)).save(buf, format="PNG")
    return buf.getvalue()


def _mock_auth(mock_supa, tipo="admin", ativo=True):
    """Delega ao helper canônico fixando user.id = _UID_SELF (self-guards).

    O user.id ser _UID_SELF é crítico: DELETE/PATCH em /usuarios/_UID_SELF
    deve bater no bloqueio de auto-edição (400). ativo=False exercita o
    gate de conta desativada (403).
    """
    return mock_auth(mock_supa, tipo=tipo, user_id=_UID_SELF, ativo=ativo)


# ── GET /configuracoes/academia ──────────────────────────────────────────────

def test_obter_academia_autenticado(client):
    """Configuração da academia: qualquer autenticado pode ler (não só admin)."""
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")
        # (B-3) maybe_single: _ler_config() usa maybe_single para evitar PGRST116
        # caso a tabela academia_config esteja vazia (ex.: antes da migration).
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": 1, "nome": "Academia Teste", "notif_dias_antes": 1}
        )
        res = client.get("/configuracoes/academia", headers=_auth_headers())
        assert res.status_code == 200
        assert res.get_json()["nome"] == "Academia Teste"


def test_obter_academia_sem_token(client):
    """Sem token → 401 (academia_config não é rota pública)."""
    res = client.get("/configuracoes/academia")
    assert res.status_code == 401


# ── PUT /configuracoes/academia ──────────────────────────────────────────────

def test_atualizar_academia_nao_admin(client):
    """Recepcionista não pode alterar as configurações da academia → 403."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")
        res = client.put("/configuracoes/academia",
                         json={"nome": "Nova"}, headers=_auth_headers())
        assert res.status_code == 403


def test_atualizar_academia_horario_invalido(client):
    """Horário com hora > 23:59 → 422 (regex HH:MM valida no schema).

    O regex `^([01]\\d|2[0-3]):[0-5]\\d$` aceita apenas 00:00–23:59.
    '25:00' é inválido — sem acessar o banco.
    """
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        res = client.put("/configuracoes/academia", json={
            "horarios": {"seg": {"abre": "25:00", "fecha": "22:00"}}
        }, headers=_auth_headers())
        assert res.status_code == 422


def test_atualizar_academia_email_invalido(client):
    """E-mail sem @ → 422 (regex _EMAIL_RE no schema)."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        res = client.put("/configuracoes/academia",
                         json={"email": "nao-eh-email"}, headers=_auth_headers())
        assert res.status_code == 422


def test_atualizar_academia_dias_antes_fora_do_limite(client):
    """notif_dias_antes > 30 → 422 (Field(ge=0, le=30) no schema)."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        res = client.put("/configuracoes/academia",
                         json={"notif_dias_antes": 99}, headers=_auth_headers())
        assert res.status_code == 422


def test_atualizar_academia_sucesso(client):
    """Atualização válida de academia → 200 com dados salvos."""
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
    """Corpo JSON vazio {} → 400 ('nenhum campo para atualizar')."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        res = client.put("/configuracoes/academia", json={}, headers=_auth_headers())
        assert res.status_code == 400


# ── PUT /auth/me ─────────────────────────────────────────────────────────────

def test_atualizar_me_sucesso(client):
    """PUT /auth/me com campos válidos (nome, telefone) → 200."""
    with patch("app.auth.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": _UID_SELF, "nome": "Novo Nome", "telefone": "11999999999"}]
        )
        res = client.put("/auth/me",
                         json={"nome": "Novo Nome", "telefone": "11999999999"},
                         headers=_auth_headers())
        assert res.status_code == 200
        assert res.get_json()["nome"] == "Novo Nome"


def test_atualizar_me_preferencias_cor_invalida(client):
    """Cor de destaque com formato errado → 422.

    PreferenciasSchema valida cor_destaque com `pattern=r'^#[0-9a-fA-F]{6}$'`.
    'azul' não é um hex válido → 422 antes de tocar o banco.
    """
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.put("/auth/me",
                         json={"preferencias": {"cor_destaque": "azul"}},
                         headers=_auth_headers())
        assert res.status_code == 422


def test_atualizar_me_corpo_vazio(client):
    """PUT /auth/me com {} → 400 (nada para atualizar)."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.put("/auth/me", json={}, headers=_auth_headers())
        assert res.status_code == 400


# ── POST /auth/change-password ───────────────────────────────────────────────

def test_trocar_senha_validacao(client):
    """Senha nova com menos de 8 chars → 422.

    ChangePasswordSchema declara `senha_nova: Senha` onde `Senha = Field(min_length=8)`.
    B-1: exigir mínimo de 8 caracteres dificulta senhas triviais.
    """
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.post("/auth/change-password",
                          json={"senha_atual": "atual", "senha_nova": "123"},
                          headers=_auth_headers())
        assert res.status_code == 422
        assert "senha_nova" in res.get_json()["fields"]


def test_trocar_senha_atual_incorreta(client):
    """Senha atual errada → 400 com campo 'senha_atual' em 'fields'.

    O handler revalida a senha ATUAL fazendo um sign_in_with_password antes
    de gravar a nova. Isso impede que um token roubado/compartilhado baste
    para trocar a senha da conta.
    """
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
        body = res.get_json()
        assert body["error"] == "Senha atual incorreta."
        assert body["fields"]["senha_atual"] == "Senha atual incorreta."


def test_trocar_senha_sucesso(client):
    """Troca de senha com credenciais corretas → 200 e update_user_by_id chamado."""
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


def test_trocar_senha_nova_igual_atual(client):
    """Nova senha igual à atual → 400 com campo 'senha_nova' em 'fields'."""
    with patch("app.auth.routes.supabase") as mock_supa, \
         patch("app.auth.routes.get_anon_client") as mock_factory, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.auth.admin.get_user_by_id.return_value = MagicMock(
            user=MagicMock(email="user@academia.com")
        )
        anon = MagicMock()  # login revalida com sucesso (senha_atual certa)
        mock_factory.return_value = anon
        res = client.post("/auth/change-password",
                          json={"senha_atual": "mesma123", "senha_nova": "mesma123"},
                          headers=_auth_headers())
        assert res.status_code == 400
        body = res.get_json()
        assert body["error"] == "A nova senha deve ser diferente da atual."
        assert body["fields"]["senha_nova"] == "A nova senha deve ser diferente da atual."


# ── GET /configuracoes/usuarios ──────────────────────────────────────────────

def test_listar_usuarios_admin(client):
    """GET /configuracoes/usuarios (admin) → 200 com lista de usuários com email.

    O endpoint cruza profiles (do banco) com auth.admin.list_users (Supabase Auth)
    para incluir o e-mail na resposta. O e-mail não é armazenado em profiles —
    fica apenas no Auth. list_users usa page=1, per_page=1000 (N-4: sem paginação
    infinita).
    """
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        prof = {
            "id": _UID1, "nome": "Ana", "tipo": "aluno",
            "telefone": None, "ativo": True, "created_at": "2024-01-01",
        }
        mock_supa.table.return_value.select.return_value.order.return_value.execute.return_value = MagicMock(
            data=[prof]
        )
        auth_user = MagicMock()
        auth_user.id = _UID1
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
    """Recepcionista não pode listar usuários → 403."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")
        res = client.get("/configuracoes/usuarios", headers=_auth_headers())
        assert res.status_code == 403


def test_listar_usuarios_sem_token(client):
    """Sem token → 401."""
    res = client.get("/configuracoes/usuarios")
    assert res.status_code == 401


# ── PATCH /configuracoes/usuarios/<id>/tipo ──────────────────────────────────

def test_alterar_tipo_sucesso(client):
    """Admin altera o tipo de outro usuário → 200."""
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        mock_supa.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": _UID1, "tipo": "instrutor"}]
        )
        # _UID1 ≠ _UID_SELF → self-guard não bloqueia
        res = client.patch(f"/configuracoes/usuarios/{_UID1}/tipo",
                           json={"tipo": "instrutor"}, headers=_auth_headers())
        assert res.status_code == 200
        assert res.get_json()["tipo"] == "instrutor"


def test_alterar_tipo_para_instrutor_cria_registro_instrutores(client):
    """Ao promover para instrutor, insere linha na tabela instrutores quando não existe.

    A tabela `instrutores` tem campos extras (especialidade, salário, etc.) que
    não existem em `profiles`. O registro é criado com esses campos nulos e pode
    ser preenchido depois na tela de edição.
    """
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")

        profiles_tbl = MagicMock()
        profiles_tbl.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": _UID2, "tipo": "instrutor"}]
        )

        instrutores_tbl = MagicMock()
        # (B-3) maybe_single: verifica se já existe registro (para não duplicar).
        instrutores_tbl.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None   # nenhum registro existente → deve inserir
        )

        mock_supa.table.side_effect = lambda name: profiles_tbl if name == "profiles" else instrutores_tbl

        res = client.patch(f"/configuracoes/usuarios/{_UID2}/tipo",
                           json={"tipo": "instrutor"}, headers=_auth_headers())
        assert res.status_code == 200
        instrutores_tbl.insert.assert_called_once_with({"profile_id": _UID2})


def test_alterar_tipo_para_instrutor_nao_duplica_registro(client):
    """Se já existe linha em instrutores, não deve inserir duplicata.

    A checagem é feita com maybe_single antes do insert — idempotente.
    """
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")

        profiles_tbl = MagicMock()
        profiles_tbl.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": _UID3, "tipo": "instrutor"}]
        )

        instrutores_tbl = MagicMock()
        instrutores_tbl.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": "inst-uuid"}   # registro já existe → não insere
        )

        mock_supa.table.side_effect = lambda name: profiles_tbl if name == "profiles" else instrutores_tbl

        res = client.patch(f"/configuracoes/usuarios/{_UID3}/tipo",
                           json={"tipo": "instrutor"}, headers=_auth_headers())
        assert res.status_code == 200
        instrutores_tbl.insert.assert_not_called()


def test_alterar_tipo_proprio_bloqueado(client):
    """Admin não pode mudar o próprio tipo → 400 (self-guard).

    Sem este bloqueio, um admin poderia rebaixar a si mesmo para aluno e
    perder o acesso sem perceber, ou escalar de volta ao admin de forma suspeita.
    """
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        # _UID_SELF == user.id definido em _mock_auth → self-guard ativa
        res = client.patch(f"/configuracoes/usuarios/{_UID_SELF}/tipo",
                           json={"tipo": "aluno"}, headers=_auth_headers())
        assert res.status_code == 400


def test_alterar_tipo_invalido(client):
    """'superadmin' não é um tipo válido → 422 (Literal no schema)."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        res = client.patch(f"/configuracoes/usuarios/{_UID1}/tipo",
                           json={"tipo": "superadmin"}, headers=_auth_headers())
        assert res.status_code == 422


def test_alterar_tipo_nao_admin(client):
    """Instrutor não pode alterar tipo de usuário → 403."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="instrutor")
        res = client.patch(f"/configuracoes/usuarios/{_UID1}/tipo",
                           json={"tipo": "admin"}, headers=_auth_headers())
        assert res.status_code == 403


def test_alterar_tipo_usuario_inexistente(client):
    """UPDATE não retorna linhas (usuário não existe) → 404."""
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        mock_supa.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]  # nenhuma linha atualizada → 404
        )
        res = client.patch(f"/configuracoes/usuarios/{_UID1}/tipo",
                           json={"tipo": "aluno"}, headers=_auth_headers())
        assert res.status_code == 404


# ── PATCH /configuracoes/usuarios/<id>/status ────────────────────────────────

def test_alterar_status_sucesso(client):
    """Admin desativa outro usuário → 200."""
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        mock_supa.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": _UID1, "ativo": False}]
        )
        res = client.patch(f"/configuracoes/usuarios/{_UID1}/status",
                           json={"ativo": False}, headers=_auth_headers())
        assert res.status_code == 200
        assert res.get_json()["ativo"] is False


def test_alterar_status_proprio_bloqueado(client):
    """Admin não pode desativar a si mesmo → 400 (self-guard).

    Sem este bloqueio, o próprio admin poderia se travar fora do sistema
    e precisaria de intervenção direta no banco para recuperar o acesso.
    """
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        res = client.patch(f"/configuracoes/usuarios/{_UID_SELF}/status",
                           json={"ativo": False}, headers=_auth_headers())
        assert res.status_code == 400


def test_alterar_status_corpo_invalido(client):
    """Corpo sem 'ativo' → 422 (campo obrigatório no UserStatusSchema)."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        res = client.patch(f"/configuracoes/usuarios/{_UID1}/status",
                           json={}, headers=_auth_headers())
        assert res.status_code == 422


def test_alterar_status_nao_admin(client):
    """Recepcionista não pode alterar status de usuário → 403."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")
        res = client.patch(f"/configuracoes/usuarios/{_UID1}/status",
                           json={"ativo": False}, headers=_auth_headers())
        assert res.status_code == 403


def test_alterar_status_usuario_inexistente(client):
    """UPDATE não retorna linhas → 404."""
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        mock_supa.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[]
        )
        res = client.patch(f"/configuracoes/usuarios/{_UID1}/status",
                           json={"ativo": True}, headers=_auth_headers())
        assert res.status_code == 404


# ── Enforcement: conta desativada perde acesso ───────────────────────────────

def test_usuario_desativado_bloqueado_no_middleware(client):
    """Token válido, mas profile.ativo=False → 403 em qualquer rota.

    O middleware verifica `ativo` após validar o JWT e antes de chamar o handler.
    Isso garante que uma conta desativada pelo admin perde o acesso imediatamente,
    mesmo que o token JWT ainda não tenha expirado.
    """
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="aluno", ativo=False)
        res = client.get("/auth/me", headers=_auth_headers())
        assert res.status_code == 403
        assert "desativada" in res.get_json()["error"].lower()


def test_login_conta_desativada_bloqueado(client):
    """Login com conta desativada (ativo=False) → 403, mesmo com senha correta.

    O login verifica `profiles.ativo` APÓS a autenticação bem-sucedida.
    Isso impede que uma conta desativada pegue tokens novos via login.
    Tokens existentes ainda são verificados pelo middleware.
    """
    with patch("app.auth.routes.supabase") as mock_supa, \
         patch("app.auth.routes.get_anon_client") as mock_factory:
        anon = MagicMock()
        anon.auth.sign_in_with_password.return_value = MagicMock(
            session=MagicMock(access_token="at", refresh_token="rt"),
            user=MagicMock(id=_UID1, email="a@academia.com"),
        )
        mock_factory.return_value = anon
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"ativo": False}  # conta desativada
        )
        res = client.post("/auth/login",
                          json={"email": "a@academia.com", "password": "secret"})
        assert res.status_code == 403
        assert "desativada" in res.get_json()["error"].lower()


def test_login_conta_ativa_sucesso(client):
    """Login com conta ativa → 200 com tokens."""
    with patch("app.auth.routes.supabase") as mock_supa, \
         patch("app.auth.routes.get_anon_client") as mock_factory:
        anon = MagicMock()
        anon.auth.sign_in_with_password.return_value = MagicMock(
            session=MagicMock(access_token="at", refresh_token="rt"),
            user=MagicMock(id=_UID1, email="a@academia.com"),
        )
        mock_factory.return_value = anon
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"ativo": True}
        )
        res = client.post("/auth/login",
                          json={"email": "a@academia.com", "password": "secret"})
        assert res.status_code == 200
        assert res.get_json()["access_token"] == "at"


# ── Avatar de usuário (admin/recepcionista alteram a foto de outro) ───────────

def _mock_profile_existe(mock_supa, existe=True):
    """Simula a checagem se o profile alvo existe antes de atualizar o avatar.

    _profile_existe() usa maybe_single para não lançar PGRST116 se o usuário
    não existir — retorna None de forma limpa, gerando 404.
    """
    mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
        data={"id": _UID} if existe else None
    )


def test_definir_avatar_usuario_admin(client):
    """Admin define a foto de qualquer usuário → 200 com avatar_url."""
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
    """Recepcionista também pode definir foto de usuário → 200."""
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
    """Instrutor não pode alterar foto de outros usuários → 403.

    @require_role("admin","recepcionista") — instrutor não está na lista.
    """
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="instrutor")
        data = {"file": (io.BytesIO(_png_bytes()), "foto.png")}
        res = client.post(f"/configuracoes/usuarios/{_UID}/avatar", headers=_auth_headers(),
                          data=data, content_type="multipart/form-data")
        assert res.status_code == 403


def test_definir_avatar_usuario_inexistente_404(client):
    """Profile alvo não existe → 404 (sem upload desnecessário)."""
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        _mock_profile_existe(mock_supa, False)
        data = {"file": (io.BytesIO(_png_bytes()), "foto.png")}
        res = client.post(f"/configuracoes/usuarios/{_UID}/avatar", headers=_auth_headers(),
                          data=data, content_type="multipart/form-data")
        assert res.status_code == 404


def test_definir_avatar_usuario_sem_arquivo_400(client):
    """Requisição sem campo 'file' → 400."""
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        _mock_profile_existe(mock_supa, True)
        res = client.post(f"/configuracoes/usuarios/{_UID}/avatar", headers=_auth_headers())
        assert res.status_code == 400


def test_remover_avatar_usuario_admin(client):
    """Admin remove foto de usuário → 200 com avatar_url=None."""
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
    """Instrutor não pode remover foto de outros → 403."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="instrutor")
        res = client.delete(f"/configuracoes/usuarios/{_UID}/avatar", headers=_auth_headers())
        assert res.status_code == 403


# ── POST /configuracoes/usuarios ─────────────────────────────────────────────

def test_criar_usuario_admin_sucesso(client):
    """Admin cria novo usuário do sistema (não aluno) → 201."""
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")

        novo_user = MagicMock()
        novo_user.id = "novo-uuid"
        mock_supa.auth.admin.create_user.return_value = MagicMock(user=novo_user)
        mock_supa.table.return_value.insert.return_value.execute.return_value = MagicMock(data=[{}])

        res = client.post("/configuracoes/usuarios",
                          json={"nome": "Ana Souza", "email": "ana@academia.com",
                                "senha": "senha123", "tipo": "recepcionista"},
                          headers=_auth_headers())
        assert res.status_code == 201
        body = res.get_json()
        assert body["email"] == "ana@academia.com"
        assert body["tipo"] == "recepcionista"
        assert body["ativo"] is True


def test_criar_usuario_tipo_instrutor_cria_registro(client):
    """Ao criar usuário do tipo instrutor, deve inserir linha na tabela instrutores."""
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")

        novo_user = MagicMock()
        novo_user.id = "inst-novo-uuid"
        mock_supa.auth.admin.create_user.return_value = MagicMock(user=novo_user)

        instrutores_tbl = MagicMock()
        profiles_tbl = MagicMock()
        mock_supa.table.side_effect = lambda name: instrutores_tbl if name == "instrutores" else profiles_tbl

        client.post("/configuracoes/usuarios",
                    json={"nome": "Carlos", "email": "carlos@academia.com",
                          "senha": "senha123", "tipo": "instrutor"},
                    headers=_auth_headers())

        instrutores_tbl.insert.assert_called_once_with({"profile_id": "inst-novo-uuid"})


def test_criar_usuario_nao_admin_bloqueado(client):
    """Recepcionista não pode criar usuários → 403."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")
        res = client.post("/configuracoes/usuarios",
                          json={"nome": "X", "email": "x@x.com", "senha": "123456", "tipo": "admin"},
                          headers=_auth_headers())
        assert res.status_code == 403


def test_criar_usuario_tipo_aluno_bloqueado(client):
    """Schema bloqueia tipo='aluno': alunos exigem CPF e usam fluxo próprio.

    CriarUsuarioSchema declara `tipo: Literal['admin','recepcionista','instrutor']`.
    'aluno' não está no Literal → 422. Alunos são criados por POST /alunos.
    """
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        res = client.post("/configuracoes/usuarios",
                          json={"nome": "Maria", "email": "maria@x.com",
                                "senha": "123456", "tipo": "aluno"},
                          headers=_auth_headers())
        assert res.status_code == 422


def test_criar_usuario_email_invalido(client):
    """E-mail sem @ → 422 (regex de email no schema)."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        res = client.post("/configuracoes/usuarios",
                          json={"nome": "X", "email": "nao-eh-email",
                                "senha": "123456", "tipo": "admin"},
                          headers=_auth_headers())
        assert res.status_code == 422


def test_criar_usuario_email_duplicado_retorna_400_com_field(client):
    """E-mail já cadastrado → 400 com campo 'email' em 'fields'.

    Simula falha do auth.admin.create_user (usuário já existe).
    Deve retornar 400 e indicar qual campo falhou.
    """
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        # Simula exceção de e-mail já registrado
        mock_supa.auth.admin.create_user.side_effect = Exception(
            "AuthApiError: User already registered"
        )

        res = client.post("/configuracoes/usuarios",
                          json={"nome": "Novo Admin",
                                "email": "ja@existe.com",
                                "senha": "Senha@1234",
                                "tipo": "admin"},
                          headers=_auth_headers())

        assert res.status_code == 400
        body = res.get_json()
        assert body["error"] == "E-mail já cadastrado."
        assert body["fields"]["email"] == "E-mail já cadastrado."
        assert "detail" not in body


# ── DELETE /configuracoes/usuarios/<id> ──────────────────────────────────────

def test_excluir_usuario_admin_sucesso(client):
    """Admin exclui outro admin (há pelo menos 2 admins) → 204.

    O mock simula [_UID_SELF, _UID_OTHER] como lista de admins.
    Como há 2 admins, excluir _UID_OTHER é permitido.
    """
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")

        # Dois admins: exclusão não bloqueada pelo "último admin"
        mock_supa.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": _UID_SELF}, {"id": _UID_OTHER}]
        )
        # _UID_OTHER não é aluno (maybe_single retorna None)
        mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )

        res = client.delete(f"/configuracoes/usuarios/{_UID_OTHER}", headers=_auth_headers())
        assert res.status_code == 204
        mock_supa.auth.admin.delete_user.assert_called_once_with(_UID_OTHER)


def test_excluir_usuario_proprio_bloqueado(client):
    """Admin não pode excluir a própria conta → 400 (self-guard).

    Sem este bloqueio, um admin poderia se excluir acidentalmente e perder
    o acesso ao sistema (potencialmente bloqueando a conta do único admin).
    """
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        res = client.delete(f"/configuracoes/usuarios/{_UID_SELF}", headers=_auth_headers())
        assert res.status_code == 400
        assert "própria" in res.get_json()["error"].lower()


def test_excluir_usuario_ultimo_admin_bloqueado(client):
    """Único admin do sistema não pode ser excluído → 400.

    Se excluíssemos o último admin, o sistema ficaria sem ninguém para
    gerenciar usuários, configurações e dados.
    """
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")

        # Apenas um admin existe — não pode excluir
        mock_supa.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": _UID_UNICO}]
        )

        res = client.delete(f"/configuracoes/usuarios/{_UID_UNICO}", headers=_auth_headers())
        assert res.status_code == 400
        assert "único administrador" in res.get_json()["error"].lower()


def test_excluir_usuario_nao_admin_bloqueado(client):
    """Recepcionista não pode excluir usuários → 403."""
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")
        res = client.delete(f"/configuracoes/usuarios/{_UID_ANON}", headers=_auth_headers())
        assert res.status_code == 403


# ── Regras de negócio: alunos com/sem mensalidades ──────────────────────────

def _mock_tabelas_aluno(mock_supa, tem_atrasada=False, tem_qualquer=False):
    """Configura mock completo para operações que verificam histórico de mensalidades.

    _mensalidades_aluno() consulta:
      1. alunos (se o usuário é aluno via profile_id)
      2. aluno_planos (quais planos o aluno tem)
      3. mensalidades (com .in_("aluno_plano_id", plano_ids)):
         - .eq("status","atrasada") → tem_atrasada
         - sem filtro de status → tem_qualquer (qualquer mensalidade)
      4. profiles (para o self-guard: lista de admins)

    O side_effect por tabela evita colisão entre queries de tabelas diferentes.
    """
    profiles_tbl = MagicMock()
    # Lista de admins para o self-guard (dois admins → exclusão não bloqueada por "último")
    profiles_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": _UID_SELF}, {"id": _UID_OTHER}]
    )
    profiles_tbl.update.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": _UID_ALUNO, "ativo": False}]
    )

    alunos_tbl = MagicMock()
    # O usuário é um aluno (maybe_single retorna registro)
    alunos_tbl.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
        data={"id": "aluno-uuid"}
    )

    planos_tbl = MagicMock()
    planos_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(
        data=[{"id": "plan-uuid"}]
    )

    mens_tbl = MagicMock()
    # Cadeia COM .eq("status","atrasada") → verifica mensalidades atrasadas
    mens_tbl.select.return_value.in_.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"id": "m1"}] if tem_atrasada else []
    )
    # Cadeia SEM .eq → verifica QUALQUER mensalidade (histórico financeiro)
    mens_tbl.select.return_value.in_.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[{"id": "m1"}] if tem_qualquer else []
    )

    def side(name):
        return {
            "profiles":     profiles_tbl,
            "alunos":       alunos_tbl,
            "aluno_planos": planos_tbl,
            "mensalidades": mens_tbl,
        }.get(name, MagicMock())

    mock_supa.table.side_effect = side


# ── PATCH status: regras para alunos ─────────────────────────────────────────

def test_desativar_aluno_com_atrasadas_bloqueado(client):
    """Desativar aluno com mensalidades em atraso → 409.

    O admin deve resolver os débitos antes de desativar a conta.
    Regra de negócio: aluno inadimplente não pode ser 'escondido' desativando.
    """
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        _mock_tabelas_aluno(mock_supa, tem_atrasada=True)

        res = client.patch(f"/configuracoes/usuarios/{_UID_ALUNO}/status",
                           json={"ativo": False}, headers=_auth_headers())
        assert res.status_code == 409
        assert "atraso" in res.get_json()["error"].lower()


def test_desativar_aluno_sem_atrasadas_permitido(client):
    """Desativar aluno sem mensalidades em atraso → 200, mesmo com histórico pago."""
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        _mock_tabelas_aluno(mock_supa, tem_atrasada=False, tem_qualquer=True)

        res = client.patch(f"/configuracoes/usuarios/{_UID_ALUNO}/status",
                           json={"ativo": False}, headers=_auth_headers())
        assert res.status_code == 200


def test_ativar_aluno_com_atrasadas_sempre_permitido(client):
    """Reativar aluno (ativo=True) nunca é bloqueado, mesmo com débitos.

    Lógica: se o admin quer reativar um aluno inadimplente, é decisão dele.
    O bloqueio só existe ao DESATIVAR (para evitar 'esconder' inadimplência).
    """
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        _mock_tabelas_aluno(mock_supa, tem_atrasada=True)

        res = client.patch(f"/configuracoes/usuarios/{_UID_ALUNO}/status",
                           json={"ativo": True}, headers=_auth_headers())
        assert res.status_code == 200


# ── DELETE: regras para alunos ───────────────────────────────────────────────

def test_excluir_aluno_com_atrasadas_bloqueado(client):
    """Excluir aluno com mensalidades em atraso → 409 com mensagem de débito."""
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        _mock_tabelas_aluno(mock_supa, tem_atrasada=True)

        res = client.delete(f"/configuracoes/usuarios/{_UID_ALUNO}", headers=_auth_headers())
        assert res.status_code == 409
        assert "atraso" in res.get_json()["error"].lower()


def test_excluir_aluno_com_historico_financeiro_bloqueado(client):
    """Excluir aluno com mensalidades (sem atraso) → 409 preservar histórico.

    Mensalidades pagas são registros contábeis imutáveis. A alternativa
    correta é Desativar (bloqueia acesso sem destruir dados).
    """
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        _mock_tabelas_aluno(mock_supa, tem_atrasada=False, tem_qualquer=True)

        res = client.delete(f"/configuracoes/usuarios/{_UID_ALUNO}", headers=_auth_headers())
        assert res.status_code == 409
        assert "histórico" in res.get_json()["error"].lower()


def test_excluir_aluno_sem_mensalidades_permitido(client):
    """Excluir aluno sem nenhuma mensalidade → 204 (cascade limpo).

    Aluno recém-cadastrado sem plano vinculado pode ser excluído fisicamente.
    O cascade FK remove os registros dependentes em outras tabelas.
    """
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        _mock_tabelas_aluno(mock_supa, tem_atrasada=False, tem_qualquer=False)

        res = client.delete(f"/configuracoes/usuarios/{_UID_ALUNO}", headers=_auth_headers())
        assert res.status_code == 204
        mock_supa.auth.admin.delete_user.assert_called_once_with(_UID_ALUNO)


# ── POST /configuracoes/usuarios/<id>/reset-senha ────────────────────────────

def test_reset_senha_admin_sucesso(client):
    """Admin redefine a senha de outro usuário → 204.

    Usa a Admin API do Supabase (update_user_by_id) — o admin não precisa
    conhecer a senha atual do usuário alvo. Útil para contas bloqueadas.
    """
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")
        mock_supa.auth.admin.update_user_by_id.return_value = MagicMock()

        res = client.post(
            f"/configuracoes/usuarios/{_UID_OTHER}/reset-senha",
            json={"senha_nova": "NovaSenha123"},
            headers=_auth_headers(),
        )
        assert res.status_code == 204
        mock_supa.auth.admin.update_user_by_id.assert_called_once_with(
            _UID_OTHER, {"password": "NovaSenha123"}
        )


def test_reset_senha_proprio_usuario_bloqueado(client):
    """Admin não pode redefinir a própria senha por este endpoint → 400.

    Para trocar a própria senha, o admin deve usar /auth/change-password,
    que exige confirmar a senha atual (mais seguro — prova posse da conta).
    """
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")

        res = client.post(
            f"/configuracoes/usuarios/{_UID_SELF}/reset-senha",
            json={"senha_nova": "NovaSenha123"},
            headers=_auth_headers(),
        )
        assert res.status_code == 400
        assert "própria senha" in res.get_json()["error"]
        mock_supa.auth.admin.update_user_by_id.assert_not_called()


def test_reset_senha_nao_admin_bloqueado(client):
    """Recepcionista não pode redefinir senha de ninguém → 403."""
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="recepcionista")

        res = client.post(
            f"/configuracoes/usuarios/{_UID_OTHER}/reset-senha",
            json={"senha_nova": "NovaSenha123"},
            headers=_auth_headers(),
        )
        assert res.status_code == 403


def test_reset_senha_curta_rejeitada(client):
    """Senha com menos de 8 caracteres é barrada pelo schema → 422.

    ResetSenhaAdminSchema declara `senha_nova: Senha` onde `Senha = Field(min_length=8)`.
    Isso aplica a mesma política de senha mínima do login e do change-password.
    """
    with patch("app.configuracoes.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="admin")

        res = client.post(
            f"/configuracoes/usuarios/{_UID_OTHER}/reset-senha",
            json={"senha_nova": "abc"},
            headers=_auth_headers(),
        )
        assert res.status_code == 422
