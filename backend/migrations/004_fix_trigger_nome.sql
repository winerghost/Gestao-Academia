-- ============================================================
-- 004_fix_trigger_nome.sql
-- Rodar no SQL Editor do Supabase, após 003_avaliacoes.sql
--
-- Contexto / bug:
-- A função handle_new_user() que estava em produção tinha sido
-- alterada manualmente e gravava o nome do profile como o literal
-- 'admin', ignorando o nome enviado em raw_user_meta_data->>'nome'.
-- Resultado: todo aluno/instrutor novo nascia com nome "admin".
--
-- Esta migration:
--   1. Restaura a função correta (idêntica à de 001_schema_inicial.sql).
--   2. Corrige (backfill) os profiles que já foram criados errados,
--      puxando o nome real de auth.users.raw_user_meta_data.
-- ============================================================

-- ── 1. Restaura a função do trigger ─────────────────────────
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, nome, tipo)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'nome', 'Sem nome'),
        COALESCE((NEW.raw_user_meta_data->>'tipo')::tipo_usuario, 'aluno')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

-- O trigger on_auth_user_created já existe (criado em 001) e aponta
-- para esta função, então não precisa recriá-lo.

-- ── 2. Backfill dos profiles gravados errados ───────────────
-- Atualiza apenas profiles cujo nome ficou como 'admin' por causa do
-- bug, MAS que possuem um nome real no metadata do Auth.
-- Exclui o admin verdadeiro (tipo = 'admin', cujo metadata não tem nome).
UPDATE public.profiles p
SET nome = u.raw_user_meta_data->>'nome'
FROM auth.users u
WHERE u.id = p.id
  AND p.nome = 'admin'
  AND p.tipo <> 'admin'
  AND COALESCE(u.raw_user_meta_data->>'nome', '') <> '';

-- ── Conferência (opcional) ──────────────────────────────────
-- SELECT p.id, p.nome, p.tipo, u.raw_user_meta_data->>'nome' AS meta_nome
-- FROM public.profiles p
-- JOIN auth.users u ON u.id = p.id
-- ORDER BY p.created_at;
