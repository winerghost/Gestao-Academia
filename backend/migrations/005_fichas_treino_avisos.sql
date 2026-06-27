-- ============================================================
-- 005_fichas_treino_avisos.sql
-- Fichas de treino dos alunos e avisos da academia
-- Rodar após 004_fix_trigger_nome.sql, no SQL Editor do Supabase.
-- Idempotente: pode ser executado mais de uma vez sem erro.
-- ============================================================

-- ── fichas_treino ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fichas_treino (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id     UUID NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    instrutor_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    nome         TEXT NOT NULL,           -- ex.: "Ficha A – Peito e Tríceps"
    divisao      CHAR(1),                 -- A, B, C, D (opcional)
    ativa        BOOLEAN NOT NULL DEFAULT TRUE,
    observacoes  TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── exercicios_ficha ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS exercicios_ficha (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ficha_id     UUID NOT NULL REFERENCES fichas_treino(id) ON DELETE CASCADE,
    nome         TEXT NOT NULL,
    series       SMALLINT,
    repeticoes   TEXT,            -- "8-12", "15", "falha" — texto por ser range
    carga_kg     NUMERIC(6, 2),
    descanso_seg SMALLINT,
    ordem        SMALLINT NOT NULL DEFAULT 0,
    observacoes  TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── avisos ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS avisos (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    titulo       TEXT NOT NULL,
    mensagem     TEXT NOT NULL,
    tipo         TEXT NOT NULL DEFAULT 'info'
                 CHECK (tipo IN ('info', 'aviso', 'urgente')),
    ativo        BOOLEAN NOT NULL DEFAULT TRUE,
    data_inicio  DATE NOT NULL DEFAULT CURRENT_DATE,
    data_fim     DATE,                    -- NULL = sem prazo de validade
    criado_por   UUID REFERENCES profiles(id) ON DELETE SET NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── Índices ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_fichas_treino_aluno_id ON fichas_treino(aluno_id);
CREATE INDEX IF NOT EXISTS idx_fichas_treino_ativa    ON fichas_treino(ativa);
CREATE INDEX IF NOT EXISTS idx_exercicios_ficha_id    ON exercicios_ficha(ficha_id);
CREATE INDEX IF NOT EXISTS idx_avisos_ativo           ON avisos(ativo);
CREATE INDEX IF NOT EXISTS idx_avisos_datas           ON avisos(data_inicio, data_fim);

-- ── RLS ───────────────────────────────────────────────────────────────────────
ALTER TABLE fichas_treino    ENABLE ROW LEVEL SECURITY;
ALTER TABLE exercicios_ficha ENABLE ROW LEVEL SECURITY;
ALTER TABLE avisos           ENABLE ROW LEVEL SECURITY;

-- fichas_treino
DROP POLICY IF EXISTS "fichas_treino: admin gerencia tudo"            ON fichas_treino;
CREATE POLICY "fichas_treino: admin gerencia tudo"
    ON fichas_treino FOR ALL
    USING (get_user_tipo() = 'admin');

DROP POLICY IF EXISTS "fichas_treino: instrutor gerencia alunos seus" ON fichas_treino;
CREATE POLICY "fichas_treino: instrutor gerencia alunos seus"
    ON fichas_treino FOR ALL
    USING (
        get_user_tipo() = 'instrutor' AND
        aluno_id IN (
            SELECT ap.aluno_id
            FROM aluno_planos ap
            JOIN instrutor_planos ip ON ip.plano_id = ap.plano_id
            JOIN instrutores i ON i.id = ip.instrutor_id
            WHERE i.profile_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "fichas_treino: aluno ve as suas"               ON fichas_treino;
CREATE POLICY "fichas_treino: aluno ve as suas"
    ON fichas_treino FOR SELECT
    USING (
        aluno_id IN (
            SELECT id FROM alunos WHERE profile_id = auth.uid()
        )
    );

-- exercicios_ficha
DROP POLICY IF EXISTS "exercicios_ficha: admin gerencia tudo"         ON exercicios_ficha;
CREATE POLICY "exercicios_ficha: admin gerencia tudo"
    ON exercicios_ficha FOR ALL
    USING (get_user_tipo() = 'admin');

DROP POLICY IF EXISTS "exercicios_ficha: instrutor gerencia via ficha" ON exercicios_ficha;
CREATE POLICY "exercicios_ficha: instrutor gerencia via ficha"
    ON exercicios_ficha FOR ALL
    USING (
        get_user_tipo() = 'instrutor' AND
        ficha_id IN (
            SELECT ft.id FROM fichas_treino ft
            JOIN aluno_planos ap ON ap.aluno_id = ft.aluno_id
            JOIN instrutor_planos ip ON ip.plano_id = ap.plano_id
            JOIN instrutores i ON i.id = ip.instrutor_id
            WHERE i.profile_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "exercicios_ficha: aluno ve os seus"            ON exercicios_ficha;
CREATE POLICY "exercicios_ficha: aluno ve os seus"
    ON exercicios_ficha FOR SELECT
    USING (
        ficha_id IN (
            SELECT ft.id FROM fichas_treino ft
            JOIN alunos a ON a.id = ft.aluno_id
            WHERE a.profile_id = auth.uid()
        )
    );

-- avisos
DROP POLICY IF EXISTS "avisos: admin gerencia tudo"            ON avisos;
CREATE POLICY "avisos: admin gerencia tudo"
    ON avisos FOR ALL
    USING (get_user_tipo() = 'admin');

DROP POLICY IF EXISTS "avisos: autenticados visualizam ativos" ON avisos;
CREATE POLICY "avisos: autenticados visualizam ativos"
    ON avisos FOR SELECT
    USING (ativo = TRUE);
