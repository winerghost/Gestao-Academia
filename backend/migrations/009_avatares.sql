-- ============================================================
-- 009_avatares.sql
-- Foto de perfil do usuário: coluna avatar_url + bucket de Storage.
-- Rodar após as migrations anteriores, no SQL Editor do Supabase.
-- ============================================================

-- ------------------------------------------------------------
-- profiles.avatar_url
-- URL pública da foto do usuário. Pode apontar para:
--   - um objeto do bucket `avatars` (foto enviada pelo usuário), ou
--   - uma URL do Gravatar (quando o usuário opta por usar o Gravatar dele).
-- NULL = sem foto → o frontend cai no avatar de iniciais.
-- ------------------------------------------------------------
ALTER TABLE profiles
    ADD COLUMN IF NOT EXISTS avatar_url TEXT;

-- ------------------------------------------------------------
-- Bucket de avatares (PÚBLICO)
-- Avatares são de baixa sensibilidade; um bucket público dispensa
-- signed URLs e funciona direto em <img src>. O upload/remoção é feito
-- pelo backend com a service role, então a escrita já é controlada na
-- aplicação. As policies abaixo são defesa em profundidade caso algum
-- dia o frontend passe a enviar direto com o JWT do usuário.
-- ------------------------------------------------------------
INSERT INTO storage.buckets (id, name, public)
VALUES ('avatars', 'avatars', TRUE)
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- RLS de storage.objects para o bucket `avatars`
-- Convenção de path: "<user_id>/<arquivo>" — cada usuário só mexe na
-- própria pasta. auth.uid() é o dono; o 1º segmento do path é o user_id.
-- ============================================================

-- Leitura pública (o bucket já é público, mas deixamos explícito).
CREATE POLICY "avatars: leitura publica"
    ON storage.objects FOR SELECT
    USING (bucket_id = 'avatars');

-- Cada usuário só insere arquivos dentro da própria pasta.
CREATE POLICY "avatars: dono insere"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'avatars'
        AND auth.uid()::text = (storage.foldername(name))[1]
    );

-- Cada usuário só atualiza arquivos da própria pasta.
CREATE POLICY "avatars: dono atualiza"
    ON storage.objects FOR UPDATE
    USING (
        bucket_id = 'avatars'
        AND auth.uid()::text = (storage.foldername(name))[1]
    );

-- Cada usuário só remove arquivos da própria pasta.
CREATE POLICY "avatars: dono remove"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'avatars'
        AND auth.uid()::text = (storage.foldername(name))[1]
    );
