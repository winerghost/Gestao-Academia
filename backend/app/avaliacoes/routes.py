import io
from xml.sax.saxutils import escape as xml_escape
from flask import Blueprint, request, jsonify, send_file, g, current_app
from ..supabase_client import supabase
from ..auth.middleware import require_auth, require_role
from ..validation import data_iso_valida, uuid_valido, validate_body
from ..schemas import AvaliacaoCreateSchema, AvaliacaoUpdateSchema

avaliacoes_bp = Blueprint("avaliacoes", __name__, url_prefix="/avaliacoes")

_LIMITES_VALIDOS = frozenset({10, 25, 50, 100})

def _calcular_imc(peso_kg, altura_cm):
    try:
        if peso_kg and altura_cm and float(altura_cm) > 0:
            h = float(altura_cm) / 100
            return round(float(peso_kg) / (h ** 2), 2)
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    return None


def _alunos_do_instrutor(profile_id: str) -> list:
    """IDs dos alunos vinculados aos planos do instrutor logado.

    Usado para limitar a visibilidade do instrutor às suas avaliações,
    já que o backend usa a service_role (que ignora o RLS).
    """
    inst = (
        supabase.table("instrutores")
        .select("id")
        .eq("profile_id", profile_id)
        .maybe_single()
        .execute()
    )
    if not inst or not inst.data:
        return []

    planos = (
        supabase.table("instrutor_planos")
        .select("plano_id")
        .eq("instrutor_id", inst.data["id"])
        .execute()
    )
    plano_ids = [p["plano_id"] for p in (planos.data or [])]
    if not plano_ids:
        return []

    vinculos = (
        supabase.table("aluno_planos")
        .select("aluno_id")
        .in_("plano_id", plano_ids)
        .execute()
    )
    return list({v["aluno_id"] for v in (vinculos.data or [])})


# ── Endpoints ─────────────────────────────────────────────────────────────────

@avaliacoes_bp.get("")
@require_role("admin", "instrutor", "recepcionista")
def listar():
    aluno_id    = request.args.get("aluno_id")
    data_inicio = request.args.get("data_inicio")
    data_fim    = request.args.get("data_fim")
    busca       = request.args.get("busca", "").strip()[:100]

    try:
        limit  = int(request.args.get("limit", 25))
        offset = int(request.args.get("offset", 0))
    except (ValueError, TypeError):
        limit, offset = 25, 0

    if limit not in _LIMITES_VALIDOS:
        limit = 25
    offset = max(0, offset)

    # aluno_id: UUID na coluna do banco. Valor inválido → erro de cast do Postgres
    # exposto pelo PostgREST como 400 com texto interno. Validamos antes.
    if aluno_id is not None and not uuid_valido(aluno_id):
        return jsonify({"error": "Parâmetro 'aluno_id' deve ser um UUID válido"}), 400

    # Datas malformadas viram erro de cast no Postgres (500). Valida antes.
    for rotulo, valor in (("data_inicio", data_inicio), ("data_fim", data_fim)):
        if valor and not data_iso_valida(valor):
            return jsonify({
                "error": f"Parâmetro '{rotulo}' deve estar no formato AAAA-MM-DD"
            }), 400

    vazio = {"data": [], "total": 0, "limit": limit, "offset": offset}

    # Busca por nome: resolve os aluno_ids que batem antes de filtrar avaliacoes
    ids_busca = None
    if busca:
        match = (
            supabase.table("alunos")
            .select("id, profiles!inner(nome)")
            .filter("profiles.nome", "ilike", f"%{busca}%")
            .execute()
        )
        ids_busca = {a["id"] for a in (match.data or [])}
        if not ids_busca:
            return jsonify(vazio)

    query = (
        supabase.table("avaliacoes")
        .select(
            "id, data_avaliacao, peso_kg, altura_cm, imc, gordura_corporal, "
            "massa_magra_kg, aluno_id, instrutor_id, created_at, "
            "alunos(profiles(nome))",
            count="exact",
        )
    )

    # Combina filtros de aluno_id, busca por nome e restrição de instrutor
    if g.user_tipo == "instrutor":
        permitidos = set(_alunos_do_instrutor(g.user_id))
        if not permitidos:
            return jsonify(vazio)
        final_ids = permitidos
        if aluno_id:
            final_ids = {aluno_id} & final_ids
        if ids_busca is not None:
            final_ids &= ids_busca
        if not final_ids:
            return jsonify(vazio)
        query = query.in_("aluno_id", list(final_ids))
    elif aluno_id:
        if ids_busca is not None and aluno_id not in ids_busca:
            return jsonify(vazio)
        query = query.eq("aluno_id", aluno_id)
    elif ids_busca is not None:
        query = query.in_("aluno_id", list(ids_busca))

    if data_inicio:
        query = query.gte("data_avaliacao", data_inicio)
    if data_fim:
        query = query.lte("data_avaliacao", data_fim)

    result = (
        query
        .order("data_avaliacao", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return jsonify({
        "data":   result.data,
        "total":  result.count,
        "limit":  limit,
        "offset": offset,
    })


@avaliacoes_bp.post("")
@require_role("admin", "instrutor")
@validate_body(AvaliacaoCreateSchema)
def criar(payload: AvaliacaoCreateSchema):
    aluno_id = str(payload.aluno_id)

    aluno = (
        supabase.table("alunos")
        .select("id")
        .eq("id", aluno_id)
        .maybe_single()
        .execute()
    )
    if not aluno or not aluno.data:
        return jsonify({"error": "Aluno não encontrado"}), 404

    # Instrutor só cria avaliação para alunos dos seus planos
    if g.user_tipo == "instrutor" and aluno_id not in _alunos_do_instrutor(g.user_id):
        return jsonify({"error": "Acesso negado a este aluno"}), 403

    # mode="json" serializa UUID/date como string; exclude_none descarta os
    # campos não preenchidos (no cadastro o frontend só envia os preenchidos).
    dados = payload.model_dump(mode="json", exclude_none=True)

    # Autoria não vem do cliente: instrutor que cria é o responsável.
    # Admin pode atribuir explicitamente (instrutor_id no corpo).
    if g.user_tipo == "instrutor":
        dados["instrutor_id"] = g.user_id

    imc = _calcular_imc(dados.get("peso_kg"), dados.get("altura_cm"))
    if imc:
        dados["imc"] = imc

    try:
        result = supabase.table("avaliacoes").insert(dados).execute()
        return jsonify(result.data[0]), 201
    except Exception:  # noqa: BLE001 — detalhe vai para o log, não para o cliente
        current_app.logger.exception("Falha ao salvar avaliação")
        return jsonify({"error": "Não foi possível salvar a avaliação"}), 400


@avaliacoes_bp.get("/<uuid:avaliacao_id>")
@require_role("admin", "instrutor", "recepcionista")
def buscar(avaliacao_id):
    result = (
        supabase.table("avaliacoes")
        .select("*, alunos(id, cpf, profiles(nome, telefone))")
        .eq("id", str(avaliacao_id))
        .maybe_single()
        .execute()
    )
    if not result or not result.data:
        return jsonify({"error": "Avaliação não encontrada"}), 404

    avaliacao = result.data

    # Instrutor só acessa avaliações dos seus alunos (devolve 404 para
    # não revelar a existência do registro)
    if g.user_tipo == "instrutor" and avaliacao["aluno_id"] not in _alunos_do_instrutor(g.user_id):
        return jsonify({"error": "Avaliação não encontrada"}), 404

    if avaliacao.get("instrutor_id"):
        inst = (
            supabase.table("profiles")
            .select("nome")
            .eq("id", avaliacao["instrutor_id"])
            .maybe_single()
            .execute()
        )
        avaliacao["instrutor_nome"] = (inst.data or {}).get("nome") if inst else None

    return jsonify(avaliacao)


@avaliacoes_bp.put("/<uuid:avaliacao_id>")
@require_role("admin", "instrutor")
@validate_body(AvaliacaoUpdateSchema)
def atualizar(avaliacao_id, payload: AvaliacaoUpdateSchema):
    # exclude_unset: só os campos realmente enviados entram no UPDATE (campos
    # vazios viram None pelos validators e, exceto data_avaliacao, limpam a coluna).
    update = payload.model_dump(mode="json", exclude_unset=True)

    # data_avaliacao é NOT NULL: não permitimos apagá-la (se vier vazia → None).
    if update.get("data_avaliacao") is None:
        update.pop("data_avaliacao", None)
    # Instrutor não reassocia a autoria (instrutor_id) de uma avaliação.
    if g.user_tipo == "instrutor":
        update.pop("instrutor_id", None)

    if not update:
        return jsonify({"error": "Nenhum campo válido para atualizar"}), 400

    # Estado atual da avaliação (para ownership do instrutor e recálculo de IMC)
    atual = (
        supabase.table("avaliacoes")
        .select("aluno_id, peso_kg, altura_cm")
        .eq("id", str(avaliacao_id))
        .maybe_single()
        .execute()
    )
    if not atual or not atual.data:
        return jsonify({"error": "Avaliação não encontrada"}), 404

    # Instrutor só edita avaliações dos seus alunos
    if g.user_tipo == "instrutor" and atual.data["aluno_id"] not in _alunos_do_instrutor(g.user_id):
        return jsonify({"error": "Avaliação não encontrada"}), 404

    # Recalcula IMC se peso ou altura foi enviado
    if "peso_kg" in update or "altura_cm" in update:
        peso   = update.get("peso_kg")   if "peso_kg"   in update else atual.data.get("peso_kg")
        altura = update.get("altura_cm") if "altura_cm" in update else atual.data.get("altura_cm")
        update["imc"] = _calcular_imc(peso, altura)

    result = (
        supabase.table("avaliacoes")
        .update(update)
        .eq("id", str(avaliacao_id))
        .execute()
    )
    if not result.data:
        return jsonify({"error": "Avaliação não encontrada"}), 404
    return jsonify(result.data[0])


@avaliacoes_bp.delete("/<uuid:avaliacao_id>")
@require_role("admin")
def deletar(avaliacao_id):
    result = (
        supabase.table("avaliacoes")
        .delete()
        .eq("id", str(avaliacao_id))
        .execute()
    )
    if not result.data:
        return jsonify({"error": "Avaliação não encontrada"}), 404
    return jsonify({"message": "Avaliação excluída com sucesso"})


@avaliacoes_bp.get("/<uuid:avaliacao_id>/pdf")
@require_role("admin", "instrutor", "recepcionista")
def exportar_pdf(avaliacao_id):
    from ..relatorios.pdf import gerar_pdf

    result = (
        supabase.table("avaliacoes")
        .select("*, alunos(cpf, profiles(nome))")
        .eq("id", str(avaliacao_id))
        .maybe_single()
        .execute()
    )
    if not result or not result.data:
        return jsonify({"error": "Avaliação não encontrada"}), 404

    av = result.data

    # Mesmo guard de ownership do GET JSON: instrutor só exporta avaliações dos
    # seus alunos. Sem isto, como a rota usa a service_role (ignora RLS), um
    # instrutor exportaria o PDF de qualquer avaliação (IDOR + vazamento de PII).
    # Devolve 404 para não revelar a existência do registro.
    if g.user_tipo == "instrutor" and av["aluno_id"] not in _alunos_do_instrutor(g.user_id):
        return jsonify({"error": "Avaliação não encontrada"}), 404

    alunos = av.get("alunos") or {}
    profiles = alunos.get("profiles") or {}
    nome_aluno = profiles.get("nome") or "—"

    def fmt(v, suffix=""):
        return f"{v}{suffix}" if v is not None else "—"

    imc_class = ""
    if av.get("imc"):
        imc = float(av["imc"])
        if imc < 18.5:       imc_class = " (Abaixo do peso)"
        elif imc < 25:       imc_class = " (Normal)"
        elif imc < 30:       imc_class = " (Sobrepeso)"
        else:                imc_class = " (Obesidade)"

    headers = ["Campo", "Valor"]
    rows = [
        ["Aluno",              nome_aluno],
        ["Data da Avaliação",  fmt(av.get("data_avaliacao"))],
        ["Peso",               fmt(av.get("peso_kg"), " kg")],
        ["Altura",             fmt(av.get("altura_cm"), " cm")],
        ["IMC",                fmt(av.get("imc")) + imc_class],
        ["% Gordura Corporal", fmt(av.get("gordura_corporal"), "%")],
        ["Massa Magra",        fmt(av.get("massa_magra_kg"), " kg")],
        ["Circ. Cintura",      fmt(av.get("circ_cintura"), " cm")],
        ["Circ. Quadril",      fmt(av.get("circ_quadril"), " cm")],
        ["Circ. Braço",        fmt(av.get("circ_braco"), " cm")],
        ["Circ. Coxa",         fmt(av.get("circ_coxa"), " cm")],
        ["Circ. Peito",        fmt(av.get("circ_peito"), " cm")],
        ["Diâm. Biacromial",          fmt(av.get("diam_biacromial"), " cm")],
        ["Diâm. Tórax Transverso",    fmt(av.get("diam_torax_transverso"), " cm")],
        ["Diâm. Tórax Ântero-Post.",  fmt(av.get("diam_torax_ap"), " cm")],
        ["Diâm. Biepicôndilo Umeral", fmt(av.get("diam_biepicondilo_umeral"), " cm")],
        ["Diâm. Biestilóide",         fmt(av.get("diam_biestiloide"), " cm")],
        ["Diâm. Crista Ilíaca",       fmt(av.get("diam_crista_iliaca"), " cm")],
        ["Diâm. Bitrocantérica",      fmt(av.get("diam_bitrocanterica"), " cm")],
        ["Diâm. Biepicôndilo Femural", fmt(av.get("diam_biepicondilo_femural"), " cm")],
        ["Diâm. Bimaleolar",          fmt(av.get("diam_bimaleolar"), " cm")],
        ["Pressão Arterial",   fmt(av.get("pressao_arterial"))],
        ["Observações",        av.get("observacoes") or "—"],
    ]

    # Escapa o nome no título: gerar_pdf renderiza o título via Paragraph,
    # que interpreta markup XML do reportlab (um '<' quebraria a geração)
    titulo = f"Avaliação Física — {xml_escape(nome_aluno)}"
    buffer = gerar_pdf(titulo, headers, rows)
    # Nome do arquivo: mantém só caracteres seguros (evita injeção no
    # header Content-Disposition via nome do aluno)
    slug = "".join(c if c.isalnum() else "_" for c in nome_aluno).strip("_") or "aluno"
    nome_arquivo = f"avaliacao_{slug}_{av.get('data_avaliacao', 'sem_data')}.pdf"

    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=nome_arquivo,
    )
