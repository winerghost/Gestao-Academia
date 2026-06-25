-- ============================================================
-- 002_rls_policies.sql
-- Rodar após 001_schema_inicial.sql
-- ============================================================

-- Habilita RLS em todas as tabelas
ALTER TABLE profiles       ENABLE ROW LEVEL SECURITY;
ALTER TABLE alunos         ENABLE ROW LEVEL SECURITY;
ALTER TABLE instrutores    ENABLE ROW LEVEL SECURITY;
ALTER TABLE planos         ENABLE ROW LEVEL SECURITY;
ALTER TABLE instrutor_planos ENABLE ROW LEVEL SECURITY;
ALTER TABLE aluno_planos   ENABLE ROW LEVEL SECURITY;
ALTER TABLE mensalidades   ENABLE ROW LEVEL SECURITY;
ALTER TABLE frequencias    ENABLE ROW LEVEL SECURITY;

-- Helper: retorna o tipo do usuário logado (SECURITY DEFINER ignora RLS)
CREATE OR REPLACE FUNCTION get_user_tipo()
RETURNS tipo_usuario AS $$
    SELECT tipo FROM profiles WHERE id = auth.uid() LIMIT 1;
$$ LANGUAGE SQL SECURITY DEFINER STABLE;

-- ============================================================
-- profiles
-- ============================================================
CREATE POLICY "profiles: usuario ve o proprio"
    ON profiles FOR SELECT
    USING (id = auth.uid());

CREATE POLICY "profiles: admin e recepcionista veem todos"
    ON profiles FOR SELECT
    USING (get_user_tipo() IN ('admin', 'recepcionista'));

CREATE POLICY "profiles: admin gerencia tudo"
    ON profiles FOR ALL
    USING (get_user_tipo() = 'admin');

-- ============================================================
-- alunos
-- ============================================================
CREATE POLICY "alunos: admin e recepcionista gerenciam"
    ON alunos FOR ALL
    USING (get_user_tipo() IN ('admin', 'recepcionista'));

CREATE POLICY "alunos: instrutor ve alunos dos seus planos"
    ON alunos FOR SELECT
    USING (
        get_user_tipo() = 'instrutor' AND
        id IN (
            SELECT ap.aluno_id
            FROM aluno_planos ap
            JOIN instrutor_planos ip ON ip.plano_id = ap.plano_id
            JOIN instrutores i ON i.id = ip.instrutor_id
            WHERE i.profile_id = auth.uid()
        )
    );

CREATE POLICY "alunos: aluno ve o proprio"
    ON alunos FOR SELECT
    USING (profile_id = auth.uid());

-- ============================================================
-- instrutores
-- ============================================================
CREATE POLICY "instrutores: admin gerencia tudo"
    ON instrutores FOR ALL
    USING (get_user_tipo() = 'admin');

CREATE POLICY "instrutores: recepcionista visualiza"
    ON instrutores FOR SELECT
    USING (get_user_tipo() = 'recepcionista');

CREATE POLICY "instrutores: instrutor ve o proprio"
    ON instrutores FOR SELECT
    USING (profile_id = auth.uid());

-- ============================================================
-- planos
-- ============================================================
CREATE POLICY "planos: admin gerencia tudo"
    ON planos FOR ALL
    USING (get_user_tipo() = 'admin');

CREATE POLICY "planos: autenticados veem planos ativos"
    ON planos FOR SELECT
    USING (ativo = TRUE AND auth.uid() IS NOT NULL);

-- ============================================================
-- instrutor_planos
-- ============================================================
CREATE POLICY "instrutor_planos: admin gerencia tudo"
    ON instrutor_planos FOR ALL
    USING (get_user_tipo() = 'admin');

CREATE POLICY "instrutor_planos: autenticados visualizam"
    ON instrutor_planos FOR SELECT
    USING (auth.uid() IS NOT NULL);

-- ============================================================
-- aluno_planos
-- ============================================================
CREATE POLICY "aluno_planos: admin e recepcionista gerenciam"
    ON aluno_planos FOR ALL
    USING (get_user_tipo() IN ('admin', 'recepcionista'));

CREATE POLICY "aluno_planos: aluno ve os proprios"
    ON aluno_planos FOR SELECT
    USING (
        aluno_id IN (
            SELECT id FROM alunos WHERE profile_id = auth.uid()
        )
    );

-- ============================================================
-- mensalidades
-- ============================================================
CREATE POLICY "mensalidades: admin e recepcionista gerenciam"
    ON mensalidades FOR ALL
    USING (get_user_tipo() IN ('admin', 'recepcionista'));

CREATE POLICY "mensalidades: aluno ve as proprias"
    ON mensalidades FOR SELECT
    USING (
        aluno_plano_id IN (
            SELECT ap.id
            FROM aluno_planos ap
            JOIN alunos a ON a.id = ap.aluno_id
            WHERE a.profile_id = auth.uid()
        )
    );

-- ============================================================
-- frequencias
-- ============================================================
CREATE POLICY "frequencias: admin e recepcionista gerenciam"
    ON frequencias FOR ALL
    USING (get_user_tipo() IN ('admin', 'recepcionista'));

CREATE POLICY "frequencias: aluno ve as proprias"
    ON frequencias FOR SELECT
    USING (
        aluno_id IN (
            SELECT id FROM alunos WHERE profile_id = auth.uid()
        )
    );
