import io
from datetime import date
from xml.sax.saxutils import escape as xml_escape
from flask import Blueprint, request, jsonify, send_file, g, current_app
from ..supabase_client import supabase
from ..auth.middleware import require_auth, require_role

avaliacoes_bp = Blueprint("avaliacoes", __name__, url_prefix="/avaliacoes")

# Teto de itens na listagem — evita devolver a tabela inteira de uma vez
_LIMITE_LISTAGEM = 200

# Diâmetros ósseos (modelo "Mapeamento Corporal"), em cm.
_CAMPOS_DIAMETROS = {
    "diam_biacromial", "diam_torax_transverso", "diam_torax_ap",
    "diam_biepicondilo_umeral", "diam_biestiloide", "diam_crista_iliaca",
    "diam_bitrocanterica", "diam_biepicondilo_femural", "diam_bimaleolar",
}

_CAMPOS_NUMERICOS = {
    "peso_kg", "altura_cm", "gordura_corporal", "massa_magra_kg",
    "circ_cintura", "circ_quadril", "circ_braco", "circ_coxa", "circ_peito",
    *_CAMPOS_DIAMETROS,
}

_CAMPOS_PERMITIDOS = {
    "aluno_id", "instrutor_id", "data_avaliacao",
    "peso_kg", "altura_cm", "gordura_corporal", "massa_magra_kg",
    "circ_cintura", "circ_quadril", "circ_braco", "circ_coxa", "circ_peito",
    "pressao_arterial", "observacoes",
    *_CAMPOS_DIAMETROS,
}


def _calcular_imc(peso_kg, altura_cm):
    try:
        if peso_kg and altura_cm and float(altura_cm) > 0:
            h = float(altura_cm) / 100
            return round(float(peso_kg) / (h ** 2), 2)
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    return None


def _converter_numericos(payload: dict) -> dict | tuple:
    for campo in _CAMPOS_NUMERICOS:
        if campo in payload and payload[campo] not in (None, ""):
            try:
                payload[campo] = float(payload[campo])
            except (TypeError, ValueError):
                return None, f"Valor inválido para '{campo}'"
        elif campo in payload and payload[campo] in (None, ""):
            payload[campo] = None
    return payload, None


def _data_valida(valor) -> bool:
    """True se 'valor' é uma data ISO (YYYY-MM-DD) válida."""
    try:
        date.fromisoformat(str(valor))
        return True
    except (TypeError, ValueError):
        return False


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
    aluno_id   = request.args.get("aluno_id")
    data_inicio = request.args.get("data_inicio")
    data_fim   = request.args.get("data_fim")

    query = (
        supabase.table("avaliacoes")
        .select(
            "id, data_avaliacao, peso_kg, altura_cm, imc, gordura_corporal, "
            "massa_magra_kg, aluno_id, instrutor_id, created_at, "
            "alunos(profiles(nome))"
        )
    )

    # Instrutor só enxerga avaliações dos alunos dos seus planos
    if g.user_tipo == "instrutor":
        permitidos = _alunos_do_instrutor(g.user_id)
        if not permitidos:
            return jsonify([])
        if aluno_id and aluno_id not in permitidos:
            return jsonify([])
        query = query.in_("aluno_id", [aluno_id] if aluno_id else permitidos)
    elif aluno_id:
        query = query.eq("aluno_id", aluno_id)

    if data_inicio:
        query = query.gte("data_avaliacao", data_inicio)
    if data_fim:
        query = query.lte("data_avaliacao", data_fim)

    result = (
        query.order("data_avaliacao", desc=True)
        .limit(_LIMITE_LISTAGEM)
        .execute()
    )
    return jsonify(result.data)


@avaliacoes_bp.post("")
@require_role("admin", "instrutor")
def criar():
    data = request.get_json(silent=True) or {}

    if not data.get("aluno_id"):
        return jsonify({"error": "Campo 'aluno_id' é obrigatório"}), 400
    if not data.get("data_avaliacao"):
        return jsonify({"error": "Campo 'data_avaliacao' é obrigatório"}), 400
    if not _data_valida(data["data_avaliacao"]):
        return jsonify({"error": "Campo 'data_avaliacao' deve estar no formato AAAA-MM-DD"}), 400

    aluno = (
        supabase.table("alunos")
        .select("id")
        .eq("id", data["aluno_id"])
        .maybe_single()
        .execute()
    )
    if not aluno or not aluno.data:
        return jsonify({"error": "Aluno não encontrado"}), 404

    # Instrutor só cria avaliação para alunos dos seus planos
    if g.user_tipo == "instrutor" and data["aluno_id"] not in _alunos_do_instrutor(g.user_id):
        return jsonify({"error": "Acesso negado a este aluno"}), 403

    payload = {k: v for k, v in data.items() if k in _CAMPOS_PERMITIDOS and v not in (None, "")}
    payload, err = _converter_numericos(payload)
    if err:
        return jsonify({"error": err}), 400

    # Autoria não vem do cliente: instrutor que cria é o responsável.
    # Admin pode atribuir explicitamente (instrutor_id no corpo).
    if g.user_tipo == "instrutor":
        payload["instrutor_id"] = g.user_id

    imc = _calcular_imc(payload.get("peso_kg"), payload.get("altura_cm"))
    if imc:
        payload["imc"] = imc

    try:
        result = supabase.table("avaliacoes").insert(payload).execute()
        return jsonify(result.data[0]), 201
    except Exception as e:
        current_app.logger.exception("Falha ao salvar avaliação")
        return jsonify({"error": "Não foi possível salvar a avaliação", "detalhe": str(e)}), 400


@avaliacoes_bp.get("/<uuid:avaliacao_id>")
@require_role("admin", "instrutor", "recepcionista")
def buscar(avaliacao_id):
    result = (
        supabase.table("avaliacoes")
        .select("*, alunos(id, cpf, profiles(nome, telefone))")
        .eq("id", str(avaliacao_id))
        .single()
        .execute()
    )
    if not result.data:
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
            .single()
            .execute()
        )
        avaliacao["instrutor_nome"] = inst.data["nome"] if inst.data else None

    return jsonify(avaliacao)


@avaliacoes_bp.put("/<uuid:avaliacao_id>")
@require_role("admin", "instrutor")
def atualizar(avaliacao_id):
    data = request.get_json(silent=True) or {}

    campos_editaveis = _CAMPOS_PERMITIDOS - {"aluno_id"}
    # Instrutor não reassocia a autoria (instrutor_id) de uma avaliação
    if g.user_tipo == "instrutor":
        campos_editaveis = campos_editaveis - {"instrutor_id"}
    update = {k: v for k, v in data.items() if k in campos_editaveis}

    if not update:
        return jsonify({"error": "Nenhum campo válido para atualizar"}), 400

    if "data_avaliacao" in update and not _data_valida(update["data_avaliacao"]):
        return jsonify({"error": "Campo 'data_avaliacao' deve estar no formato AAAA-MM-DD"}), 400

    update, err = _converter_numericos(update)
    if err:
        return jsonify({"error": err}), 400

    # Estado atual da avaliação (para ownership do instrutor e recálculo de IMC)
    atual = (
        supabase.table("avaliacoes")
        .select("aluno_id, peso_kg, altura_cm")
        .eq("id", str(avaliacao_id))
        .single()
        .execute()
    )
    if not atual.data:
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
        .single()
        .execute()
    )
    if not result.data:
        return jsonify({"error": "Avaliação não encontrada"}), 404

    av = result.data
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
