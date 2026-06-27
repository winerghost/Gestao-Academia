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


# ── Alunos ───────────────────────────────────────────────────────────────────

class AlunoCreateSchema(StrictModel):
    nome: Nome
    email: Email
    senha: Senha
    cpf: str
    data_nascimento: OptDate = None
    endereco: Annotated[OptStr, Field(max_length=300)] = None
    status: Literal["ativo", "inativo"] = "ativo"
    frequencia_habilitada: bool = False

    @field_validator("cpf")
    @classmethod
    def _cpf(cls, v: str) -> str:
        return _limpar_cpf(v)


class AlunoUpdateSchema(StrictModel):
    cpf: Optional[str] = None
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


class VincularPlanoInstrutorSchema(StrictModel):
    plano_id: UUID
