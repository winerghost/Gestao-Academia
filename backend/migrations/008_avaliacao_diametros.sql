-- ============================================================
-- 008_avaliacao_diametros.sql
-- Diâmetros ósseos na avaliação física (modelo "Mapeamento Corporal").
-- Valores em centímetros (cm). Todos opcionais.
-- Rodar após as migrations anteriores.
-- ============================================================

ALTER TABLE avaliacoes
    ADD COLUMN IF NOT EXISTS diam_biacromial          NUMERIC(6, 2),  -- largura dos ombros
    ADD COLUMN IF NOT EXISTS diam_torax_transverso    NUMERIC(6, 2),  -- tórax (transverso)
    ADD COLUMN IF NOT EXISTS diam_torax_ap            NUMERIC(6, 2),  -- tórax ântero-posterior
    ADD COLUMN IF NOT EXISTS diam_biepicondilo_umeral NUMERIC(6, 2),  -- cotovelo (úmero)
    ADD COLUMN IF NOT EXISTS diam_biestiloide         NUMERIC(6, 2),  -- punho
    ADD COLUMN IF NOT EXISTS diam_crista_iliaca       NUMERIC(6, 2),  -- bacia (crista ilíaca)
    ADD COLUMN IF NOT EXISTS diam_bitrocanterica      NUMERIC(6, 2),  -- quadril (trocânteres)
    ADD COLUMN IF NOT EXISTS diam_biepicondilo_femural NUMERIC(6, 2), -- joelho (fêmur)
    ADD COLUMN IF NOT EXISTS diam_bimaleolar          NUMERIC(6, 2);  -- tornozelo
