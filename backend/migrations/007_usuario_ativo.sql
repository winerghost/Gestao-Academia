-- ============================================================
-- 007_usuario_ativo.sql
-- Permite desativar/ativar usuários (bloqueia o acesso ao sistema
-- sem apagar a conta). Fonte da verdade para o status na tela "Equipe".
-- Rodar após as migrations anteriores.
-- ============================================================

-- Usuário ativo = pode acessar o sistema. Desativado = login/uso bloqueado
-- (enforce no backend: rota de login e middleware require_auth).
-- DEFAULT TRUE garante que todas as contas existentes continuem ativas.
ALTER TABLE profiles
    ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE;
