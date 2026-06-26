-- ============================================================
-- 003_avaliacoes.sql
-- Avaliações físicas dos alunos
-- Rodar após 002_rls_policies.sql, no SQL Editor do Supabase.
-- Idempotente: pode ser executado mais de uma vez sem erro.
-- ============================================================

-- avaliacoes
CREATE TABLE IF NOT EXISTS avaliacoes (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    aluno_id         UUID NOT NULL REFERENCES alunos(id) ON DELETE CASCADE,
    -- instrutor responsável (profiles.id — o backend resolve o nome via profiles)
    instrutor_id     UUID REFERENCES profiles(id) ON DELETE SET NULL,
    data_avaliacao   DATE NOT NULL,

    -- medidas (todas opcionais; CHECK só vale quando preenchidas)
    peso_kg          NUMERIC(5, 2) CHECK (peso_kg          IS NULL OR peso_kg          > 0),
    altura_cm        NUMERIC(5, 2) CHECK (altura_cm        IS NULL OR altura_cm        > 0),
    imc              NUMERIC(5, 2) CHECK (imc              IS NULL OR imc              > 0),
    gordura_corporal NUMERIC(5, 2) CHECK (gordura_corporal IS NULL OR (gordura_corporal >= 0 AND gordura_corporal <= 100)),
    massa_magra_kg   NUMERIC(5, 2) CHECK (massa_magra_kg   IS NULL OR massa_magra_kg   >= 0),
    circ_cintura     NUMERIC(5, 2) CHECK (circ_cintura     IS NULL OR circ_cintura     >= 0),
    circ_quadril     NUMERIC(5, 2) CHECK (circ_quadril     IS NULL OR circ_quadril     >= 0),
    circ_braco       NUMERIC(5, 2) CHECK (circ_braco       IS NULL OR circ_braco       >= 0),
    circ_coxa        NUMERIC(5, 2) CHECK (circ_coxa        IS NULL OR circ_coxa        >= 0),
    circ_peito       NUMERIC(5, 2) CHECK (circ_peito       IS NULL OR circ_peito       >= 0),

    pressao_arterial TEXT,
    observacoes      TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================
-- Índices (evita full scan nos filtros de listagem)
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_avaliacoes_aluno_id ON avaliacoes(aluno_id);
CREATE INDEX IF NOT EXISTS idx_avaliacoes_data     ON avaliacoes(data_avaliacao);

-- ============================================================
-- RLS
-- Obs.: o backend usa a SERVICE_ROLE_KEY, que IGNORA o RLS — a
-- autorização real é feita pelos decorators @require_role no Flask.
-- Estas policies são defesa em profundidade: protegem o caso de
-- alguém acessar a tabela com a chave anon (ex.: cliente Supabase
-- direto), espelhando o acesso pretendido por tipo de usuário.
-- ============================================================
ALTER TABLE avaliacoes ENABLE ROW LEVEL SECURITY;

-- admin: acesso total
DROP POLICY IF EXISTS "avaliacoes: admin gerencia tudo" ON avaliacoes;
CREATE POLICY "avaliacoes: admin gerencia tudo"
    ON avaliacoes FOR ALL
    USING (get_user_tipo() = 'admin');

-- recepcionista: somente leitura
DROP POLICY IF EXISTS "avaliacoes: recepcionista visualiza" ON avaliacoes;
CREATE POLICY "avaliacoes: recepcionista visualiza"
    ON avaliacoes FOR SELECT
    USING (get_user_tipo() = 'recepcionista');

-- instrutor: lê avaliações dos alunos dos seus planos
DROP POLICY IF EXISTS "avaliacoes: instrutor ve alunos dos seus planos" ON avaliacoes;
CREATE POLICY "avaliacoes: instrutor ve alunos dos seus planos"
    ON avaliacoes FOR SELECT
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

-- instrutor: cria avaliações para os alunos dos seus planos
DROP POLICY IF EXISTS "avaliacoes: instrutor cria para seus alunos" ON avaliacoes;
CREATE POLICY "avaliacoes: instrutor cria para seus alunos"
    ON avaliacoes FOR INSERT
    WITH CHECK (
        get_user_tipo() = 'instrutor' AND
        aluno_id IN (
            SELECT ap.aluno_id
            FROM aluno_planos ap
            JOIN instrutor_planos ip ON ip.plano_id = ap.plano_id
            JOIN instrutores i ON i.id = ip.instrutor_id
            WHERE i.profile_id = auth.uid()
        )
    );

-- instrutor: edita avaliações dos alunos dos seus planos
DROP POLICY IF EXISTS "avaliacoes: instrutor edita seus alunos" ON avaliacoes;
CREATE POLICY "avaliacoes: instrutor edita seus alunos"
    ON avaliacoes FOR UPDATE
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

-- aluno: vê as próprias avaliações
DROP POLICY IF EXISTS "avaliacoes: aluno ve as proprias" ON avaliacoes;
CREATE POLICY "avaliacoes: aluno ve as proprias"
    ON avaliacoes FOR SELECT
    USING (
        aluno_id IN (
            SELECT id FROM alunos WHERE profile_id = auth.uid()
        )
    );
