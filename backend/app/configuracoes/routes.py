from datetime import datetime, timezone

from flask import Blueprint, jsonify, g
from ..supabase_client import supabase
from ..auth.middleware import require_auth, require_role
from ..schemas import AcademiaConfigSchema, UserTipoSchema, UserStatusSchema
from ..validation import validate_body

configuracoes_bp = Blueprint("configuracoes", __name__, url_prefix="/configuracoes")

# A configuração da academia mora numa única linha (id = 1).
_CONFIG_ID = 1


def _ler_config():
    return (
        supabase.table("academia_config")
        .select("*")
        .eq("id", _CONFIG_ID)
        .single()
        .execute()
    )


@configuracoes_bp.get("/usuarios")
@require_role("admin")
def listar_usuarios():
    """Lista todos os profiles com email do Supabase Auth (somente admin)."""
    # select("*") tolera a coluna `ativo` ainda não migrada (default no .get).
    profiles_result = (
        supabase.table("profiles")
        .select("*")
        .order("created_at")
        .execute()
    )
    profiles = {p["id"]: p for p in (profiles_result.data or [])}

    auth_users = supabase.auth.admin.list_users()
    user_list = auth_users if isinstance(auth_users, list) else []

    result = []
    for u in user_list:
        uid = str(u.id)
        profile = profiles.get(uid)
        if profile:
            result.append({
                "id": uid,
                "email": u.email,
                "nome": profile["nome"],
                "tipo": profile["tipo"],
                "telefone": profile.get("telefone"),
                "ativo": profile.get("ativo", True),
                "created_at": profile["created_at"],
            })

    return jsonify(result)


@configuracoes_bp.patch("/usuarios/<user_id>/tipo")
@require_role("admin")
@validate_body(UserTipoSchema)
def atualizar_tipo_usuario(user_id: str, payload: UserTipoSchema):
    """Altera o papel de um usuário (somente admin; não pode alterar o próprio)."""
    if user_id == str(g.user_id):
        return jsonify({"error": "Você não pode alterar seu próprio tipo"}), 400

    result = (
        supabase.table("profiles")
        .update({"tipo": payload.tipo})
        .eq("id", user_id)
        .execute()
    )
    if not result.data:
        return jsonify({"error": "Usuário não encontrado"}), 404

    return jsonify(result.data[0])


@configuracoes_bp.patch("/usuarios/<user_id>/status")
@require_role("admin")
@validate_body(UserStatusSchema)
def atualizar_status_usuario(user_id: str, payload: UserStatusSchema):
    """Ativa/desativa um usuário (somente admin; não pode desativar a si mesmo).

    A coluna `ativo` é a fonte da verdade — o login e o `require_auth` bloqueiam
    quem está desativado, então a conta não é apagada, só perde o acesso.
    """
    if user_id == str(g.user_id):
        return jsonify({"error": "Você não pode desativar sua própria conta"}), 400

    result = (
        supabase.table("profiles")
        .update({"ativo": payload.ativo})
        .eq("id", user_id)
        .execute()
    )
    if not result.data:
        return jsonify({"error": "Usuário não encontrado"}), 404

    return jsonify(result.data[0])


@configuracoes_bp.get("/academia")
@require_auth
def obter_academia():
    """Configuração da academia — qualquer usuário autenticado pode ler."""
    result = _ler_config()
    return jsonify(result.data)


@configuracoes_bp.put("/academia")
@require_role("admin")
@validate_body(AcademiaConfigSchema)
def atualizar_academia(payload: AcademiaConfigSchema):
    """Atualiza dados cadastrais, horários e notificações (somente admin)."""
    update = payload.model_dump(exclude_unset=True)
    if not update:
        return jsonify({"error": "Nenhum campo válido para atualizar"}), 400

    update["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = (
        supabase.table("academia_config")
        .update(update)
        .eq("id", _CONFIG_ID)
        .execute()
    )
    if not result.data:
        return jsonify({"error": "Configuração não encontrada"}), 404
    return jsonify(result.data[0])
