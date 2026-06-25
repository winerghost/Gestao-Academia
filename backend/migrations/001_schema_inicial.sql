-- ============================================================
-- 001_schema_inicial.sql
-- Rodar no SQL Editor do Supabase
-- ============================================================

-- Enums
CREATE TYPE tipo_usuario AS ENUM ('admin', 'recepcionista', 'instrutor', 'aluno');
CREATE TYPE status_aluno AS ENUM ('ativo', 'inativo', 'inadimplente');
CREATE TYPE status_aluno_plano AS ENUM ('ativo', 'cancelado', 'encerrado');
CREATE TYPE status_mensalidade AS ENUM ('pendente', 'paga', 'atrasada');

-- profiles (estende auth.users do Supabase)
CREATE TABLE profiles (
    id         UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    nome       TEXT NOT NULL,
    tipo       tipo_usuario NOT NULL DEFAULT 'aluno',
    telefone   TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- alunos
CREATE TABLE alunos (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id            UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    cpf                   TEXT UNIQUE NOT NULL,
    data_nascimento       DATE,
    endereco              TEXT,
    status                status_aluno NOT NULL DEFAULT 'ativo',
    frequencia_habilitada BOOLEAN NOT NULL DEFAULT FALSE,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- instrutores
CREATE TABLE instrutores (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id     UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    especialidade  TEXT,
    modalidade     TEXT,
    salario        NUMERIC(10, 2),
    data_admissao  DATE,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- planos
CREATE TABLE planos (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome         TEXT NOT NULL,
    descricao    TEXT,
    valor        NUMERIC(10, 2) NOT NULL,
    duracao_dias INTEGER NOT NULL,
    ativo        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- instrutor_planos (N:N — um plano pode ter vários instrutores)
CREATE TABLE instrutor_planos (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    instrutor_id UUID NOT NULL REFERENCES instrutores(id) ON DELETE CASCADE,
    plano_id     UUID NOT NULL REFERENCES planos(id) ON DELETE CASCADE,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (instrutor_id, plano_id)
);

-- aluno_planos (N:N — um aluno pode ter vários planos)
CREATE TABLE aluno_planos (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id    UUID NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    plano_id    UUID NOT NULL REFERENCES planos(id) ON DELETE CASCADE,
    data_inicio DATE NOT NULL,
    data_fim    DATE,
    status      status_aluno_plano NOT NULL DEFAULT 'ativo',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- mensalidades (geradas automaticamente a cada ciclo do aluno_plano)
CREATE TABLE mensalidades (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_plano_id  UUID NOT NULL REFERENCES aluno_planos(id) ON DELETE CASCADE,
    valor           NUMERIC(10, 2) NOT NULL,
    juros           NUMERIC(10, 2) NOT NULL DEFAULT 0,
    valor_total     NUMERIC(10, 2) GENERATED ALWAYS AS (valor + juros) STORED,
    data_vencimento DATE NOT NULL,
    data_pagamento  DATE,
    status          status_mensalidade NOT NULL DEFAULT 'pendente',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- frequencias (somente quando alunos.frequencia_habilitada = true)
CREATE TABLE frequencias (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id   UUID NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    data_hora  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Índices
-- ============================================================
CREATE INDEX idx_alunos_status         ON alunos(status);
CREATE INDEX idx_alunos_profile_id     ON alunos(profile_id);
CREATE INDEX idx_mensalidades_status   ON mensalidades(status);
CREATE INDEX idx_mensalidades_vcto     ON mensalidades(data_vencimento);
CREATE INDEX idx_mensalidades_ap_id    ON mensalidades(aluno_plano_id);
CREATE INDEX idx_aluno_planos_aluno_id ON aluno_planos(aluno_id);
CREATE INDEX idx_frequencias_aluno_id  ON frequencias(aluno_id);

-- ============================================================
-- Trigger: cria profile automaticamente ao cadastrar usuário
-- ============================================================
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO profiles (id, nome, tipo)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'nome', 'Sem nome'),
        COALESCE((NEW.raw_user_meta_data->>'tipo')::tipo_usuario, 'aluno')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();
