from flask import Blueprint, request, jsonify, g
from gotrue.errors import AuthApiError
from ..supabase_client import supabase
from .middleware import require_auth

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "E-mail e senha são obrigatórios"}), 400

    try:
        response = supabase.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
    except AuthApiError as e:
        return jsonify({"error": "Credenciais inválidas"}), 401

    return jsonify({
        "access_token": response.session.access_token,
        "user": {
            "id": response.user.id,
            "email": response.user.email,
        },
    })


@auth_bp.post("/logout")
@require_auth
def logout():
    token = request.headers.get("Authorization", "")[7:]
    try:
        supabase.auth.sign_out()
    except AuthApiError:
        pass
    return jsonify({"message": "Logout realizado com sucesso"})


@auth_bp.get("/me")
@require_auth
def me():
    """Retorna o perfil do usuário logado."""
    result = (
        supabase.table("profiles")
        .select("id, nome, tipo, telefone, created_at")
        .eq("id", g.user_id)
        .single()
        .execute()
    )
    return jsonify(result.data)
