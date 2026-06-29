-- ============================================================
-- 012_permissoes_relatorios.sql
-- Controle de acesso granular a relatórios financeiros para
-- o cargo Recepcionista.
--
-- Por padrão, Recepcionista NÃO tem acesso ao Relatório
-- Financeiro nem ao Relatório de Inadimplência — apenas ao
-- Relatório de Alunos. O Admin habilita em Configurações →
-- Academia → Permissões.
--
-- Rodar no SQL Editor do Supabase (DEPOIS de 011).
-- Idempotente: pode rodar mais de uma vez sem efeito colateral.
-- ============================================================

ALTER TABLE academia_config
    ADD COLUMN IF NOT EXISTS permissoes_recepcionista JSONB NOT NULL
    DEFAULT '{"relatorio_financeiro": false, "relatorio_inadimplencia": false}'::jsonb;

-- Garante que a linha singleton já tenha o valor padrão caso a coluna
-- tenha sido adicionada sem DEFAULT (cenário improvável, mas defensivo).
UPDATE academia_config
    SET permissoes_recepcionista = '{"relatorio_financeiro": false, "relatorio_inadimplencia": false}'::jsonb
    WHERE permissoes_recepcionista IS NULL;
