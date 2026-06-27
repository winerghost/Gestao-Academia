-- ============================================================
-- 006_configuracoes.sql
-- Configurações da academia (linha única) + preferências por usuário.
-- Rodar após as migrations anteriores.
-- ============================================================

-- ------------------------------------------------------------
-- academia_config
-- Tabela "singleton": guarda os dados do negócio, os horários de
-- funcionamento e os parâmetros das notificações de cobrança.
-- O CHECK (id = 1) garante que só exista UMA linha de configuração.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS academia_config (
    id                   INT PRIMARY KEY DEFAULT 1,

    -- Dados cadastrais
    nome                 TEXT,
    cnpj                 TEXT,
    telefone             TEXT,
    email                TEXT,
    endereco             TEXT,

    -- Horários de funcionamento por dia da semana.
    -- Formato: { "seg": {"abre":"06:00","fecha":"22:00","fechado":false}, ... }
    horarios             JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Notificações de mensalidade (lidas pelos jobs agendados)
    notif_lembrete_ativo BOOLEAN NOT NULL DEFAULT TRUE,
    notif_dias_antes     INT     NOT NULL DEFAULT 1,
    notif_atraso_ativo   BOOLEAN NOT NULL DEFAULT TRUE,

    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT academia_config_singleton CHECK (id = 1),
    CONSTRAINT academia_config_dias_antes CHECK (notif_dias_antes BETWEEN 0 AND 30)
);

-- Cria a linha de configuração inicial (idempotente).
INSERT INTO academia_config (id) VALUES (1)
ON CONFLICT (id) DO NOTHING;

-- ------------------------------------------------------------
-- Preferências de aparência por usuário (cor de destaque, fonte…)
-- ------------------------------------------------------------
ALTER TABLE profiles
    ADD COLUMN IF NOT EXISTS preferencias JSONB NOT NULL DEFAULT '{}'::jsonb;

-- ============================================================
-- RLS — defesa em profundidade (o backend usa service role,
-- mas as policies protegem caso algo consulte com o JWT do usuário).
-- ============================================================
ALTER TABLE academia_config ENABLE ROW LEVEL SECURITY;

-- Qualquer usuário autenticado pode LER a configuração (nome, horários…).
CREATE POLICY "academia_config: autenticados leem"
    ON academia_config FOR SELECT
    USING (auth.uid() IS NOT NULL);

-- Só admin pode alterar a configuração.
CREATE POLICY "academia_config: admin gerencia"
    ON academia_config FOR ALL
    USING (get_user_tipo() = 'admin');
