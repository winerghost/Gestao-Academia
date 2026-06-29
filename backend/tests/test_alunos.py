"""Testes de alunos: CRUD, vínculos com planos e controles de segurança.

Conceitos testados:
  BOLA / IDOR via RLS
    GET /alunos/<id> usa `get_user_client(token)` — client com a IDENTIDADE
    do usuário logado. O Supabase RLS decide o que esse usuário pode ver:
      - admin/recepcionista: todos os alunos.
      - instrutor: apenas alunos dos seus planos.
      - aluno: apenas a si mesmo.
    Sem isso (usando service_role), qualquer autenticado veria qualquer aluno.

  Validação de entrada (schemas Pydantic)
    CPF: removemos não-dígitos e validamos 11 dígitos.
    Senha: mínimo 8 caracteres (B-1).
    Foto: data URL validada por regex + tamanho máximo + Pillow no backend.
    extra='forbid': campos não declarados no schema → 422 imediato.

  Upload de avatar seguro
    A imagem é sempre re-encodada com Pillow ANTES de criar o usuário no Auth.
    Isso garante: (a) imagem inválida não cria usuário órfão, (b) EXIF e
    payloads embutidos são descartados (sanitização no backend).

  Gravatar prevalece sobre foto da webcam
    Se o e-mail do aluno tem Gravatar, ele é usado automaticamente e a foto
    da webcam é ignorada — simplifica o fluxo e evita conteúdo duplicado.

  Anti-duplicidade de vínculo aluno↔plano
    Um aluno não pode ter o mesmo plano ativo mais de uma vez (409).
    A checagem na aplicação é amigável; o índice único parcial no banco
    é a garantia definitiva contra race conditions.

  Soft delete vs exclusão física
    DELETE sem ?permanente cancela o vínculo (status='cancelado') mas mantém
    o histórico. Com ?permanente=true: bloqueia se houver mensalidade PAGA.

Padrão de mock:
  _mock_auth: configura o `supabase` do middleware (módulo diferente do handler).
  Para rotas que consultam múltiplas tabelas, usamos `table.side_effect` para
  rotear por nome, evitando que mocks de tabelas diferentes se sobreponham.
"""
import base64
import io
from unittest.mock import patch, MagicMock

import pytest
from PIL import Image

from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _png_dataurl():
    """Gera uma data URL de PNG válida para testar upload de foto.

    O backend valida o formato (regex de data URL) E re-encoda com Pillow.
    Precisamos de uma imagem PNG real para passar na validação de Pillow.
    """
    buf = io.BytesIO()
    Image.new("RGB", (24, 24), (10, 200, 50)).save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _auth_headers():
    return {"Authorization": "Bearer token-fake"}


def _mock_auth(mock_supa, tipo="admin"):
    """Simula usuário autenticado no middleware.

    O middleware busca o profile para saber o tipo do usuário. Mockamos
    .single e .maybe_single (o middleware usa .maybe_single após o fix B-3).
    """
    user = MagicMock()
    user.id = "user-uuid"
    mock_supa.auth.get_user.return_value = MagicMock(user=user)
    perfil = MagicMock(data={"tipo": tipo})
    mock_supa.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = perfil
    mock_supa.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = perfil


# ── Listar alunos ─────────────────────────────────────────────────────────────

def test_listar_alunos_sem_token(client):
    """GET /alunos sem token → 401. Alunos exigem admin/recepcionista autenticado."""
    res = client.get("/alunos")
    assert res.status_code == 401


def test_listar_alunos_como_admin(client):
    """GET /alunos com admin → 200 com lista paginada {data, total, limit, offset}.

    A paginação usa `limit` filtrado por whitelist {25,50,100,200} para evitar
    queries sem limite que poderiam derrubar o banco com dados grandes.
    """
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        execute_result = MagicMock(
            data=[{"id": "uuid-1", "cpf": "12345678901", "status": "ativo"}],
            count=1,
        )
        chain = MagicMock()
        chain.order.return_value.range.return_value.execute.return_value = execute_result
        mock_supa.table.return_value.select.return_value.order = chain.order

        res = client.get("/alunos", headers=_auth_headers())
        assert res.status_code == 200
        body = res.get_json()
        assert "data" in body
        assert "total" in body
        assert body["total"] == 1
        assert isinstance(body["data"], list)


# ── Criar aluno ───────────────────────────────────────────────────────────────

def test_criar_aluno_campos_obrigatorios(client):
    """Corpo sem campos obrigatórios → 422 com lista dos campos faltando.

    AlunoCreateSchema declara nome, email, senha, cpf como obrigatórios.
    O Pydantic valida antes de chegar ao handler — sem tocar o Supabase Auth.
    """
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.post("/alunos", json={"nome": "João"}, headers=_auth_headers())
        assert res.status_code == 422
        assert {"email", "senha", "cpf"} <= set(res.get_json()["fields"])


def test_criar_aluno_cpf_invalido(client):
    """CPF com menos de 11 dígitos → 422.

    O validator _limpar_cpf remove não-dígitos e exige exatamente 11 dígitos.
    Isso impede tanto CPFs formatados errados (ex.: 'ABC') quanto CPFs curtos.
    """
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.post("/alunos", json={
            "nome": "João", "email": "j@j.com", "senha": "Senha@123", "cpf": "123"
        }, headers=_auth_headers())
        assert res.status_code == 422
        assert "cpf" in res.get_json()["fields"]


def test_criar_aluno_sucesso(client):
    """Cadastro completo com campos válidos → 201.

    Ordem de operações no handler:
      1. Valida/processa a foto (Pillow) — ANTES de criar no Auth.
      2. Cria usuário no Supabase Auth (trigger cria o profile).
      3. Define avatar (Gravatar prevalece; foto vai se não há Gravatar).
      4. Atualiza profile (telefone + avatar_url).
      5. Insere linha na tabela alunos.
    Se o insert de alunos falhar, o usuário do Auth é revertido (rollback).
    """
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.alunos.routes.gravatar_existe", return_value=False), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        user = MagicMock()
        user.id = "novo-uuid"
        mock_supa.auth.admin.create_user.return_value = MagicMock(user=user)
        mock_supa.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "novo-uuid", "cpf": "12345678901", "status": "ativo"}]
        )

        res = client.post("/alunos", json={
            "nome": "João Silva",
            "email": "joao@academia.com",
            "senha": "Senha@123",
            "cpf": "123.456.789-01",
        }, headers=_auth_headers())
        assert res.status_code == 201


def test_criar_aluno_email_duplicado_nao_vaza_detalhe(client):
    """E-mail já cadastrado → 400 com mensagem amigável, sem texto interno da exceção.

    O handler captura a exceção do Supabase Auth e verifica se é duplicidade
    de e-mail. A mensagem de erro da exceção nunca é exposta ao cliente —
    evita vazar que 'User already registered' (enumeration de usuários).
    """
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        mock_supa.auth.admin.create_user.side_effect = Exception(
            "AuthApiError: User already registered"
        )

        res = client.post("/alunos", json={
            "nome": "João Silva",
            "email": "existe@academia.com",
            "senha": "Senha@123",
            "cpf": "123.456.789-01",
        }, headers=_auth_headers())

        assert res.status_code == 400
        body = res.get_json()
        assert body["error"] == "E-mail já cadastrado"
        assert "detail" not in body   # não expõe o texto cru da exceção


# ── Buscar por id (BOLA/IDOR via RLS) ─────────────────────────────────────────

def test_buscar_aluno_usa_client_rls(client):
    """GET /alunos/<id> consulta sob a identidade do usuário (RLS ativo).

    `get_user_client(token)` cria um client Supabase autenticado com o JWT
    do usuário — diferente do client global de service_role que ignora RLS.
    O assert_called_once() prova que o handler usou o client correto.
    """
    with patch("app.alunos.routes.get_user_client") as mock_uc, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="aluno")
        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": "aluno-uuid", "cpf": "12345678901"}
        )
        mock_uc.return_value = db

        res = client.get(
            "/alunos/00000000-0000-0000-0000-000000000001",
            headers=_auth_headers(),
        )
        assert res.status_code == 200
        mock_uc.assert_called_once()  # prova o uso do client com RLS


def test_buscar_aluno_rls_nega_retorna_404(client):
    """RLS não retorna linha para aluno alheio → 404 (não revela existência).

    Retornar 403 ("acesso negado") revelaria que o registro existe.
    Retornar 404 ("não encontrado") não vaza informação sobre outros alunos.
    """
    with patch("app.alunos.routes.get_user_client") as mock_uc, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth, tipo="aluno")
        db = MagicMock()
        db.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data=None
        )
        mock_uc.return_value = db

        res = client.get(
            "/alunos/00000000-0000-0000-0000-000000000002",
            headers=_auth_headers(),
        )
        assert res.status_code == 404


# ── Telefone no cadastro ──────────────────────────────────────────────────────

def test_criar_aluno_com_telefone_atualiza_profile(client):
    """Quando telefone é enviado, deve atualizar profiles após criar o usuário.

    O trigger do Supabase só popula nome e tipo no profile — telefone precisa
    de uma segunda escrita. O side_effect roteia por tabela para testar isso.
    """
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.alunos.routes.gravatar_existe", return_value=False), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        user = MagicMock()
        user.id = "novo-uuid"
        mock_supa.auth.admin.create_user.return_value = MagicMock(user=user)

        update_chain = MagicMock()
        update_chain.eq.return_value.execute.return_value = MagicMock(data=[{}])

        insert_chain = MagicMock()
        insert_chain.execute.return_value = MagicMock(
            data=[{"id": "novo-uuid", "cpf": "12345678901", "status": "ativo"}]
        )

        def table_router(name):
            m = MagicMock()
            if name == "profiles":
                m.update.return_value = update_chain
            else:
                m.insert.return_value = insert_chain
            return m

        mock_supa.table.side_effect = table_router

        res = client.post("/alunos", json={
            "nome": "João Silva",
            "email": "joao@academia.com",
            "senha": "Senha@123",
            "cpf": "123.456.789-01",
            "telefone": "(11) 99999-9999",
        }, headers=_auth_headers())

        assert res.status_code == 201
        update_chain.eq.assert_called_once_with("id", "novo-uuid")


def test_criar_aluno_sem_telefone_nao_chama_profiles_update(client):
    """Sem telefone no payload, profiles.update não deve ser chamado.

    O handler só atualiza profiles se há algo para atualizar (telefone ou avatar).
    Escritas desnecessárias aumentam latência e criam concorrência desnecessária.
    """
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.alunos.routes.gravatar_existe", return_value=False), \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        user = MagicMock()
        user.id = "novo-uuid"
        mock_supa.auth.admin.create_user.return_value = MagicMock(user=user)
        mock_supa.table.return_value.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "novo-uuid", "cpf": "12345678901", "status": "ativo"}]
        )

        res = client.post("/alunos", json={
            "nome": "João Silva",
            "email": "joao@academia.com",
            "senha": "Senha@123",
            "cpf": "123.456.789-01",
        }, headers=_auth_headers())

        assert res.status_code == 201
        for call_args in mock_supa.table.call_args_list:
            assert call_args[0][0] != "profiles"


def test_atualizar_aluno_telefone_vai_para_profiles(client):
    """PUT /alunos/<id> com telefone atualiza profiles (não a tabela alunos).

    A tabela `alunos` não tem coluna `telefone` — ela fica em `profiles`.
    O handler busca o profile_id do aluno e atualiza profiles separadamente.
    """
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        profile_update = MagicMock()
        profile_update.eq.return_value.execute.return_value = MagicMock(data=[{}])

        aluno_select = MagicMock()
        aluno_select.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"profile_id": "profile-uuid"}
        )

        aluno_update = MagicMock()
        aluno_update.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "aluno-uuid", "cpf": "12345678901"}]
        )

        def table_router(name):
            m = MagicMock()
            if name == "profiles":
                m.update.return_value = profile_update
            else:
                m.select.return_value = aluno_select
                m.update.return_value = aluno_update
            return m

        mock_supa.table.side_effect = table_router

        res = client.put(
            "/alunos/00000000-0000-0000-0000-000000000001",
            json={"telefone": "(11) 88888-8888", "endereco": "Rua Nova, 10"},
            headers=_auth_headers(),
        )

        assert res.status_code == 200
        profile_update.eq.assert_called_once_with("id", "profile-uuid")


# ── Foto no cadastro (webcam/arquivo) + Gravatar ──────────────────────────────

def _mock_create_user(mock_supa, uid="novo-uuid"):
    """Helper: simula criação de usuário no Supabase Auth."""
    user = MagicMock()
    user.id = uid
    mock_supa.auth.admin.create_user.return_value = MagicMock(user=user)


def test_criar_aluno_gravatar_prevalece_sobre_foto(client):
    """Se o e-mail tem Gravatar, ele prevalece e a foto da webcam não sobe.

    Lógica de precedência: Gravatar > foto da webcam > sem foto (iniciais).
    O Gravatar é verificado via requisição HTTP ao gravatar.com (mockada aqui).
    Quando existe, a URL do Gravatar é salva em profiles.avatar_url diretamente
    (sem subir nada ao Storage). `upload_avatar` não deve ser chamado.
    """
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.alunos.routes.gravatar_existe", return_value=True), \
         patch("app.alunos.routes.url_gravatar", return_value="https://gravatar.com/avatar/abc"), \
         patch("app.alunos.routes.upload_avatar") as mock_upload, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        _mock_create_user(mock_supa)

        profiles_tbl = MagicMock()
        profiles_tbl.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        alunos_tbl = MagicMock()
        alunos_tbl.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "novo-uuid", "cpf": "12345678901", "status": "ativo"}]
        )
        mock_supa.table.side_effect = lambda n: profiles_tbl if n == "profiles" else alunos_tbl

        res = client.post("/alunos", json={
            "nome": "João", "email": "j@j.com", "senha": "Senha@123",
            "cpf": "123.456.789-01", "foto": _png_dataurl(),
        }, headers=_auth_headers())

        assert res.status_code == 201
        mock_upload.assert_not_called()  # Gravatar prevaleceu → foto não foi ao Storage
        profiles_tbl.update.assert_called_once_with(
            {"avatar_url": "https://gravatar.com/avatar/abc"}
        )


def test_criar_aluno_sem_gravatar_sobe_foto_webcam(client):
    """Sem Gravatar, a foto enviada é processada e sobe ao Storage.

    `processar_imagem_base64` re-encoda a imagem com Pillow (descarta EXIF).
    `upload_avatar` sobe o JPEG resultante ao Supabase Storage.
    A URL retornada é salva em profiles.avatar_url.
    """
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.alunos.routes.gravatar_existe", return_value=False), \
         patch("app.alunos.routes.upload_avatar", return_value="https://cdn.fake/u/abc.jpg") as mock_upload, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        _mock_create_user(mock_supa)

        profiles_tbl = MagicMock()
        profiles_tbl.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        alunos_tbl = MagicMock()
        alunos_tbl.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "novo-uuid", "cpf": "12345678901", "status": "ativo"}]
        )
        mock_supa.table.side_effect = lambda n: profiles_tbl if n == "profiles" else alunos_tbl

        res = client.post("/alunos", json={
            "nome": "João", "email": "j@j.com", "senha": "Senha@123",
            "cpf": "123.456.789-01", "foto": _png_dataurl(),
        }, headers=_auth_headers())

        assert res.status_code == 201
        mock_upload.assert_called_once()
        profiles_tbl.update.assert_called_once_with(
            {"avatar_url": "https://cdn.fake/u/abc.jpg"}
        )


def test_criar_aluno_foto_formato_invalido_422(client):
    """data URL que não é imagem → 422 ANTES de criar o usuário.

    A validação de formato acontece no schema (regex _FOTO_DATAURL_RE) antes
    de qualquer chamada ao Supabase Auth. Isso evita um usuário órfão no Auth
    caso a imagem fosse inválida mas o usuário já tivesse sido criado.
    """
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.post("/alunos", json={
            "nome": "João", "email": "j@j.com", "senha": "Senha@123",
            "cpf": "123.456.789-01", "foto": "data:text/plain;base64,QUJD",
        }, headers=_auth_headers())
        assert res.status_code == 422
        assert "foto" in res.get_json()["fields"]
        mock_supa.auth.admin.create_user.assert_not_called()  # usuário não foi criado


def test_criar_aluno_foto_corrompida_400(client):
    """data URL de imagem com base64 inválido para Pillow → 400, sem criar usuário.

    A validação com Pillow (processar_imagem_base64) acontece no handler,
    ANTES de criar o usuário no Auth. Imagem corrompida → 400 e nenhum usuário
    órfão fica no Supabase Auth.
    """
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.post("/alunos", json={
            "nome": "João", "email": "j@j.com", "senha": "Senha@123",
            "cpf": "123.456.789-01", "foto": "data:image/png;base64,QUJD",
        }, headers=_auth_headers())
        assert res.status_code == 400
        mock_supa.auth.admin.create_user.assert_not_called()


# ── Status ────────────────────────────────────────────────────────────────────

def test_status_invalido(client):
    """Status fora do Literal['ativo','inativo','inadimplente'] → 422.

    AlunoStatusSchema usa Literal para aceitar apenas valores do enum de status.
    'bloqueado' não existe — o Pydantic rejeita antes de chegar ao banco.
    """
    with patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        res = client.patch(
            "/alunos/00000000-0000-0000-0000-000000000001/status",
            json={"status": "bloqueado"},
            headers=_auth_headers(),
        )
        assert res.status_code == 422


# ── Vínculos aluno ↔ plano: regra anti-duplicidade + gestão ──────────────────

_ALUNO = "00000000-0000-0000-0000-000000000001"
_VINC  = "00000000-0000-0000-0000-000000000002"
_PLANO = "00000000-0000-0000-0000-000000000009"


def test_vincular_plano_duplicado_bloqueia_409(client):
    """Plano já ativo para o aluno → 409 e nenhuma inserção/mensalidade.

    A checagem na aplicação devolve uma mensagem amigável. O índice único
    parcial `uq_aluno_planos_ativo` é a garantia definitiva no banco
    (mitiga race conditions que burlariam a checagem).
    """
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.mensalidades.jobs.criar_mensalidade") as mock_cm, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        planos_tbl = MagicMock()
        # (B-3) maybe_single: busca o plano sem PGRST116.
        planos_tbl.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"valor": 99.9}
        )
        ap_tbl = MagicMock()
        ap_tbl.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[{"id": "ap-existente"}]  # vínculo ativo já existe → bloqueado
        )
        mock_supa.table.side_effect = lambda n: planos_tbl if n == "planos" else ap_tbl

        res = client.post(
            f"/alunos/{_ALUNO}/planos",
            json={"plano_id": _PLANO, "data_inicio": "2026-06-01"},
            headers=_auth_headers(),
        )
        assert res.status_code == 409
        ap_tbl.insert.assert_not_called()
        mock_cm.assert_not_called()


def test_vincular_plano_novo_sucesso(client):
    """Sem vínculo ativo do plano → insere e gera a 1ª mensalidade.

    `criar_mensalidade` é chamada com o valor do plano e a data_inicio
    como vencimento da primeira cobrança.
    """
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.mensalidades.jobs.criar_mensalidade") as mock_cm, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)

        planos_tbl = MagicMock()
        planos_tbl.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"valor": 99.9}
        )
        ap_tbl = MagicMock()
        ap_tbl.select.return_value.eq.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(
            data=[]  # nenhum vínculo ativo → pode inserir
        )
        ap_tbl.insert.return_value.execute.return_value = MagicMock(
            data=[{"id": "novo-ap", "aluno_id": _ALUNO, "plano_id": _PLANO}]
        )
        mock_supa.table.side_effect = lambda n: planos_tbl if n == "planos" else ap_tbl

        res = client.post(
            f"/alunos/{_ALUNO}/planos",
            json={"plano_id": _PLANO, "data_inicio": "2026-06-01"},
            headers=_auth_headers(),
        )
        assert res.status_code == 201
        mock_cm.assert_called_once()


def test_editar_vinculo_plano(client):
    """PUT /alunos/<id>/planos/<vinc_id> atualiza as datas do vínculo."""
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        ap_tbl = MagicMock()
        ap_tbl.update.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": _VINC, "data_fim": "2026-12-31"}]
        )
        mock_supa.table.return_value = ap_tbl

        res = client.put(
            f"/alunos/{_ALUNO}/planos/{_VINC}",
            json={"data_fim": "2026-12-31"},
            headers=_auth_headers(),
        )
        assert res.status_code == 200
        assert res.get_json()["data_fim"] == "2026-12-31"


def test_cancelar_vinculo_soft(client):
    """DELETE sem ?permanente → soft-delete (status='cancelado').

    O histórico de mensalidades é preservado no banco. Útil para fins
    contábeis e auditorias — nunca destruímos dados financeiros sem confirmação.
    """
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        ap_tbl = MagicMock()
        ap_tbl.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": _VINC}
        )
        ap_tbl.update.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        mock_supa.table.return_value = ap_tbl

        res = client.delete(f"/alunos/{_ALUNO}/planos/{_VINC}", headers=_auth_headers())
        assert res.status_code == 200
        assert "cancelado" in res.get_json()["message"]
        ap_tbl.delete.assert_not_called()  # nenhum DELETE físico foi feito


def test_excluir_vinculo_bloqueia_com_mensalidade_paga(client):
    """DELETE ?permanente com mensalidade paga → 409, sem exclusão física.

    Mensalidade paga é registro financeiro imutável — excluí-la seria
    fraude contábil. O handler verifica antes de deletar e bloqueia.
    """
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        ap_tbl = MagicMock()
        ap_tbl.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": _VINC}
        )
        mens_tbl = MagicMock()
        mens_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"status": "paga"}, {"status": "pendente"}]
        )
        mock_supa.table.side_effect = lambda n: mens_tbl if n == "mensalidades" else ap_tbl

        res = client.delete(
            f"/alunos/{_ALUNO}/planos/{_VINC}?permanente=true", headers=_auth_headers()
        )
        assert res.status_code == 409
        ap_tbl.delete.assert_not_called()


def test_excluir_vinculo_sem_paga_sucesso(client):
    """DELETE ?permanente sem mensalidade paga → exclui (cascade nas não pagas).

    Mensalidades pendentes/atrasadas sem histórico de pagamento podem ser
    excluídas em cascata via FK ON DELETE CASCADE no banco.
    """
    with patch("app.alunos.routes.supabase") as mock_supa, \
         patch("app.auth.middleware.supabase") as mock_auth:
        _mock_auth(mock_auth)
        ap_tbl = MagicMock()
        ap_tbl.select.return_value.eq.return_value.eq.return_value.maybe_single.return_value.execute.return_value = MagicMock(
            data={"id": _VINC}
        )
        ap_tbl.delete.return_value.eq.return_value.execute.return_value = MagicMock(data=[{}])
        mens_tbl = MagicMock()
        mens_tbl.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"status": "pendente"}, {"status": "atrasada"}]
        )
        mock_supa.table.side_effect = lambda n: mens_tbl if n == "mensalidades" else ap_tbl

        res = client.delete(
            f"/alunos/{_ALUNO}/planos/{_VINC}?permanente=true", headers=_auth_headers()
        )
        assert res.status_code == 200
        assert "excluído" in res.get_json()["message"]
        ap_tbl.delete.assert_called_once()
