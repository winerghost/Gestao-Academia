-- ============================================================
-- 011_unicidade_planos_mensalidades.sql
-- Rodar no SQL Editor do Supabase (DEPOIS de 010).
--
-- Contexto / problema:
--   - Um mesmo aluno podia receber o MESMO plano vinculado mais de uma vez
--     (ex.: Italo Oliveira com "Musculação" 2x), porque não havia constraint
--     impedindo dois vínculos ATIVOS para (aluno_id, plano_id).
--   - Cada vínculo gera a 1ª mensalidade → cobranças duplicadas.
--   - Não havia unicidade por (aluno_plano_id, data_vencimento), então o job
--     de geração também não tinha garantia de banco contra duplicatas.
--
-- Esta migration faz, NESTA ORDEM (saneamento ANTES dos índices, senão a
-- criação do índice único falharia com os duplicados ainda presentes):
--   1. Cancela vínculos ATIVOS duplicados de (aluno_id, plano_id), mantendo
--      o "vencedor": o que tiver mensalidade PAGA; na ausência, o mais antigo.
--   2. Remove as mensalidades NÃO PAGAS dos vínculos perdedores (as pagas
--      nunca são apagadas — preservam histórico financeiro).
--   3. Remove mensalidades duplicadas por (aluno_plano_id, data_vencimento),
--      mantendo a paga / mais antiga e apagando apenas extras NÃO pagos.
--   4. Cria índice único PARCIAL: no máximo 1 vínculo ATIVO por (aluno, plano).
--   5. Cria índice único: no máximo 1 mensalidade por (vínculo, vencimento).
--
-- Idempotente: pode rodar mais de uma vez sem efeito colateral.
-- ============================================================

BEGIN;

-- ── 1. Cancela vínculos ativos duplicados (mantém vencedor) ──────────────────
WITH ativos AS (
    SELECT
        ap.id,
        ap.aluno_id,
        ap.plano_id,
        ap.created_at,
        EXISTS (
            SELECT 1 FROM mensalidades m
            WHERE m.aluno_plano_id = ap.id AND m.status = 'paga'
        ) AS tem_paga
    FROM aluno_planos ap
    WHERE ap.status = 'ativo'
),
ranqueados AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY aluno_id, plano_id
            -- vencedor = tem pagamento primeiro; depois o mais antigo
            ORDER BY tem_paga DESC, created_at ASC, id ASC
        ) AS rn
    FROM ativos
)
UPDATE aluno_planos
SET status = 'cancelado'
WHERE id IN (SELECT id FROM ranqueados WHERE rn > 1);

-- ── 2. Remove mensalidades NÃO pagas dos vínculos recém-cancelados ──────────-
-- (Só as não pagas; pagas permanecem como histórico. A FK é ON DELETE CASCADE,
--  mas aqui a remoção é seletiva por status, então é explícita.)
DELETE FROM mensalidades m
USING aluno_planos ap
WHERE m.aluno_plano_id = ap.id
  AND ap.status = 'cancelado'
  AND m.status <> 'paga'
  AND EXISTS (  -- só nos pares (aluno, plano) que TÊM um vínculo ativo vencedor
      SELECT 1 FROM aluno_planos v
      WHERE v.aluno_id = ap.aluno_id
        AND v.plano_id = ap.plano_id
        AND v.status = 'ativo'
  );

-- ── 3. Remove mensalidades duplicadas por (vínculo, vencimento) ─────────────-
WITH ranqueadas AS (
    SELECT
        id,
        ROW_NUMBER() OVER (
            PARTITION BY aluno_plano_id, data_vencimento
            ORDER BY (status = 'paga') DESC, created_at ASC, id ASC
        ) AS rn
    FROM mensalidades
)
DELETE FROM mensalidades
WHERE status <> 'paga'
  AND id IN (SELECT id FROM ranqueadas WHERE rn > 1);

-- ── 4. Unicidade: 1 vínculo ATIVO por (aluno, plano) ────────────────────────-
-- Índice PARCIAL: cancelados/encerrados não contam, então um aluno pode
-- recontratar o mesmo plano depois de cancelar o anterior.
CREATE UNIQUE INDEX IF NOT EXISTS uq_aluno_planos_ativo
    ON aluno_planos (aluno_id, plano_id)
    WHERE status = 'ativo';

-- ── 5. Unicidade: 1 mensalidade por (vínculo, vencimento) ───────────────────-
CREATE UNIQUE INDEX IF NOT EXISTS uq_mensalidades_ap_vcto
    ON mensalidades (aluno_plano_id, data_vencimento);

COMMIT;

-- ── Conferência (opcional) ──────────────────────────────────────────────────
-- Vínculos ativos duplicados restantes (deve retornar 0 linhas):
-- SELECT aluno_id, plano_id, COUNT(*)
-- FROM aluno_planos WHERE status = 'ativo'
-- GROUP BY aluno_id, plano_id HAVING COUNT(*) > 1;
--
-- Mensalidades duplicadas restantes (deve retornar 0 linhas):
-- SELECT aluno_plano_id, data_vencimento, COUNT(*)
-- FROM mensalidades
-- GROUP BY aluno_plano_id, data_vencimento HAVING COUNT(*) > 1;
