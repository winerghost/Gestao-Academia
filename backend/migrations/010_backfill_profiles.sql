-- ============================================================
-- 010_backfill_profiles.sql
-- Rodar no SQL Editor do Supabase
--
-- Contexto:
-- Usuários criados manualmente via dashboard do Supabase (ou via
-- Admin API sem metadados) não disparam o trigger on_auth_user_created
-- em alguns cenários, ficando sem registro na tabela profiles.
-- Sem esse registro, o middleware require_auth retorna 401 e o
-- usuário fica preso na tela de erro sem poder sair.
--
-- Esta migration:
--   1. Insere profiles ausentes para todos os usuários em auth.users.
--   2. O nome é extraído do metadata (campo 'nome') ou, na ausência,
--      da parte local do e-mail (antes do @).
--   3. O tipo padrão é 'aluno' — ajuste manualmente se necessário.
-- ============================================================

INSERT INTO public.profiles (id, nome, tipo)
SELECT
    u.id,
    COALESCE(
        NULLIF(u.raw_user_meta_data->>'nome', ''),
        NULLIF(u.raw_user_meta_data->>'full_name', ''),
        split_part(u.email, '@', 1)
    ) AS nome,
    COALESCE(
        (NULLIF(u.raw_user_meta_data->>'tipo', ''))::tipo_usuario,
        'aluno'
    ) AS tipo
FROM auth.users u
LEFT JOIN public.profiles p ON p.id = u.id
WHERE p.id IS NULL
ON CONFLICT (id) DO NOTHING;

-- ── Conferência (opcional) ──────────────────────────────────
-- SELECT p.id, p.nome, p.tipo, u.email
-- FROM public.profiles p
-- JOIN auth.users u ON u.id = p.id
-- ORDER BY p.created_at DESC;
