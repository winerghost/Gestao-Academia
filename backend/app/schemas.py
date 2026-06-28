"""Schemas Pydantic para validação estrita das entradas da API.

Princípios:
- `extra="forbid"`: rejeita campos não declarados (mitiga mass-assignment e
  pega payloads malformados vindos do frontend, tratado como não confiável).
- `str_strip_whitespace`: remove espaços nas pontas (sanitização básica).
- Campos opcionais aceitam "" e viram None (o frontend manda string vazia em
  inputs não preenchidos; "" não pode ir para colunas date/numeric).
- A proteção contra SQL injection vem do PostgREST (consultas parametrizadas)
  somada a esta validação de tipos/formatos — nunca montamos SQL por string.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Annotated, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator

# Regex de e-mail propositalmente simples: a validação forte fica a cargo do
# Supabase Auth. Aqui só barramos lixo óbvio.
_EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


def _empty_to_none(v):
    if isinstance(v, str) and v.strip() == "":
        return None
    return v


OptStr = Annotated[Optional[str], BeforeValidator(_empty_to_none)]
OptDate = Annotated[Optional[date], BeforeValidator(_empty_to_none)]
OptFloat = Annotated[Optional[float], BeforeValidator(_empty_to_none)]
# UUID opcional que aceita "" (input vazio do frontend) como ausência (None).
OptUUID = Annotated[Optional[UUID], BeforeValidator(_empty_to_none)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def _limpar_cpf(v: str) -> str:
    digitos = re.sub(r"\D", "", v or "")
    if len(digitos) != 11:
        raise ValueError("CPF deve conter 11 dígitos")
    return digitos


Email = Annotated[str, Field(min_length=3, max_length=254, pattern=_EMAIL_RE)]
Senha = Annotated[str, Field(min_length=6, max_length=128)]
Nome = Annotated[str, Field(min_length=1, max_length=120)]


# ── Auth ─────────────────────────────────────────────────────────────────────

class LoginSchema(StrictModel):
    email: Email
    password: Annotated[str, Field(min_length=1, max_length=128)]


class PreferenciasSchema(StrictModel):
    """Preferências visuais do usuário."""
    cor_destaque:    Annotated[OptStr, Field(pattern=r"^#[0-9a-fA-F]{6}$")] = None
    tamanho_fonte:   Optional[Literal["pequena", "normal", "grande"]] = None
    modo:            Optional[Literal["claro", "escuro", "sistema"]] = None
    sidebar_compacta: Optional[bool] = None


class ProfileUpdateSchema(StrictModel):
    """Atualização do próprio perfil (Conta / Aparência)."""
    nome: Annotated[Optional[str], Field(min_length=1, max_length=120)] = None
    telefone: Annotated[OptStr, Field(max_length=20)] = None
    # Preferências de aparência (chaves controladas pelo PreferenciasSchema).
    preferencias: Optional[PreferenciasSchema] = None


class ChangePasswordSchema(StrictModel):
    senha_atual: Annotated[str, Field(min_length=1, max_length=128)]
    senha_nova: Senha


# ── Alunos ───────────────────────────────────────────────────────────────────

# Foto enviada como data URL base64 (webcam ou arquivo). O conteúdo real é
# revalidado e re-encodado no backend (Pillow); aqui só barramos formato/tamanho
# óbvios antes de decodificar.
_FOTO_DATAURL_RE = re.compile(r"^data:image/(?:jpeg|jpg|png|webp);base64,[A-Za-z0-9+/=\s]+$")
_FOTO_MAX_LEN = 8_000_000  # ~6 MB já decodificado; webcam gera muito menos


class AlunoCreateSchema(StrictModel):
    nome: Nome
    email: Email
    senha: Senha
    cpf: str
    telefone: Annotated[OptStr, Field(max_length=20)] = None
    data_nascimento: OptDate = None
    endereco: Annotated[OptStr, Field(max_length=300)] = None
    status: Literal["ativo", "inativo"] = "ativo"
    frequencia_habilitada: bool = False
    # Foto opcional (data URL). Decodificada e sanitizada no backend.
    foto: OptStr = None

    @field_validator("cpf")
    @classmethod
    def _cpf(cls, v: str) -> str:
        return _limpar_cpf(v)

    @field_validator("foto")
    @classmethod
    def _foto(cls, v):
        if v is None:
            return None
        if len(v) > _FOTO_MAX_LEN:
            raise ValueError("Foto muito grande")
        if not _FOTO_DATAURL_RE.match(v):
            raise ValueError("Foto deve ser uma imagem (data URL base64) JPG, PNG ou WEBP")
        return v


class AlunoUpdateSchema(StrictModel):
    cpf: Optional[str] = None
    telefone: Annotated[OptStr, Field(max_length=20)] = None
    data_nascimento: OptDate = None
    endereco: Annotated[OptStr, Field(max_length=300)] = None
    frequencia_habilitada: Optional[bool] = None

    @field_validator("cpf")
    @classmethod
    def _cpf(cls, v):
        return _limpar_cpf(v) if v not in (None, "") else None


class AlunoStatusSchema(StrictModel):
    status: Literal["ativo", "inativo", "inadimplente"]


# ── Instrutores ──────────────────────────────────────────────────────────────

class InstrutorCreateSchema(StrictModel):
    nome: Nome
    email: Email
    senha: Senha
    especialidade: Annotated[OptStr, Field(max_length=120)] = None
    modalidade: Annotated[OptStr, Field(max_length=120)] = None
    salario: Annotated[OptFloat, Field(ge=0)] = None
    data_admissao: OptDate = None


class InstrutorUpdateSchema(StrictModel):
    especialidade: Annotated[OptStr, Field(max_length=120)] = None
    modalidade: Annotated[OptStr, Field(max_length=120)] = None
    salario: Annotated[OptFloat, Field(ge=0)] = None
    data_admissao: OptDate = None


# ── Planos ───────────────────────────────────────────────────────────────────

class PlanoCreateSchema(StrictModel):
    nome: Nome
    descricao: Annotated[OptStr, Field(max_length=2000)] = None
    valor: Annotated[float, Field(gt=0)]
    duracao_dias: Annotated[int, Field(gt=0)]


class PlanoUpdateSchema(StrictModel):
    nome: Annotated[Optional[str], Field(min_length=1, max_length=120)] = None
    descricao: Annotated[OptStr, Field(max_length=2000)] = None
    valor: Annotated[Optional[float], Field(gt=0)] = None
    duracao_dias: Annotated[Optional[int], Field(gt=0)] = None


# ── Vínculos ─────────────────────────────────────────────────────────────────

class VincularPlanoAlunoSchema(StrictModel):
    plano_id: UUID
    data_inicio: date
    data_fim: OptDate = None


class AlunoPlanoUpdateSchema(StrictModel):
    """Edição de um vínculo aluno↔plano já existente.

    O `plano_id` NÃO é editável (trocar de plano = cancelar e criar outro
    vínculo, para preservar a rastreabilidade das mensalidades). Permite ajustar
    as datas e o status (incl. cancelar via status='cancelado')."""
    data_inicio: OptDate = None
    data_fim: OptDate = None
    status: Optional[Literal["ativo", "cancelado", "encerrado"]] = None


class VincularPlanoInstrutorSchema(StrictModel):
    plano_id: UUID


# ── Configurações da academia ────────────────────────────────────────────────

_HORA_RE = r"^([01]\d|2[0-3]):[0-5]\d$"  # HH:MM 24h


class HorarioDiaSchema(StrictModel):
    abre: Annotated[OptStr, Field(pattern=_HORA_RE)] = None
    fecha: Annotated[OptStr, Field(pattern=_HORA_RE)] = None
    fechado: bool = False


class UserTipoSchema(StrictModel):
    tipo: Literal["admin", "recepcionista", "instrutor", "aluno"]


class UserStatusSchema(StrictModel):
    ativo: bool


# ── Configurações da academia ────────────────────────────────────────────────

class AcademiaConfigSchema(StrictModel):
    """Atualização da configuração da academia (todos os campos opcionais)."""
    nome: Annotated[OptStr, Field(max_length=120)] = None
    cnpj: Annotated[OptStr, Field(max_length=18)] = None
    telefone: Annotated[OptStr, Field(max_length=20)] = None
    email: Annotated[OptStr, Field(max_length=254, pattern=_EMAIL_RE)] = None
    endereco: Annotated[OptStr, Field(max_length=300)] = None
    # Horários por dia: { "seg": {abre, fecha, fechado}, ... }
    horarios: Optional[dict[Literal["seg", "ter", "qua", "qui", "sex", "sab", "dom"], HorarioDiaSchema]] = None
    notif_lembrete_ativo: Optional[bool] = None
    notif_dias_antes: Annotated[Optional[int], Field(ge=0, le=30)] = None
    notif_atraso_ativo: Optional[bool] = None


# ── Avaliações físicas ─────────────────────────────────────────────────────────

class _AvaliacaoMedidas(StrictModel):
    """Campos de medida (todos opcionais), comuns à criação e à edição.

    As faixas espelham os CHECKs do banco e barram valores negativos/absurdos
    já na borda — assim o Postgres não recusa lá na frente (500 + vazamento).
    `imc` não entra: é calculado no backend, nunca recebido do cliente.
    """
    peso_kg:          Annotated[OptFloat, Field(gt=0, le=600)] = None
    altura_cm:        Annotated[OptFloat, Field(gt=0, le=300)] = None
    gordura_corporal: Annotated[OptFloat, Field(ge=0, le=100)] = None
    massa_magra_kg:   Annotated[OptFloat, Field(ge=0, le=600)] = None
    circ_cintura:     Annotated[OptFloat, Field(ge=0, le=300)] = None
    circ_quadril:     Annotated[OptFloat, Field(ge=0, le=300)] = None
    circ_braco:       Annotated[OptFloat, Field(ge=0, le=300)] = None
    circ_coxa:        Annotated[OptFloat, Field(ge=0, le=300)] = None
    circ_peito:       Annotated[OptFloat, Field(ge=0, le=300)] = None
    # Diâmetros ósseos (modelo "Mapeamento Corporal"), em cm.
    diam_biacromial:           Annotated[OptFloat, Field(ge=0, le=100)] = None
    diam_torax_transverso:     Annotated[OptFloat, Field(ge=0, le=100)] = None
    diam_torax_ap:             Annotated[OptFloat, Field(ge=0, le=100)] = None
    diam_biepicondilo_umeral:  Annotated[OptFloat, Field(ge=0, le=100)] = None
    diam_biestiloide:          Annotated[OptFloat, Field(ge=0, le=100)] = None
    diam_crista_iliaca:        Annotated[OptFloat, Field(ge=0, le=100)] = None
    diam_bitrocanterica:       Annotated[OptFloat, Field(ge=0, le=100)] = None
    diam_biepicondilo_femural: Annotated[OptFloat, Field(ge=0, le=100)] = None
    diam_bimaleolar:           Annotated[OptFloat, Field(ge=0, le=100)] = None
    pressao_arterial: Annotated[OptStr, Field(max_length=20)] = None
    observacoes:      Annotated[OptStr, Field(max_length=2000)] = None


class AvaliacaoCreateSchema(_AvaliacaoMedidas):
    aluno_id: UUID
    data_avaliacao: date
    # Autoria: instrutor que cria é forçado no backend; admin pode atribuir.
    instrutor_id: OptUUID = None


class AvaliacaoUpdateSchema(_AvaliacaoMedidas):
    # Na edição tudo é opcional; aluno_id não é editável (não está aqui).
    data_avaliacao: OptDate = None
    instrutor_id: OptUUID = None
