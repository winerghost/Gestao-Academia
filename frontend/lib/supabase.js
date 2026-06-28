import { createClient } from '@supabase/supabase-js'

// Cliente Supabase no lado do cliente — EXCLUSIVAMENTE para gerenciamento de sessão.
// Uso permitido: getSession(), setSession(), signOut().
// NUNCA use para queries de dados (from().select(), insert(), etc.).
// Todo acesso a dados passa pelo Flask via lib/api.js → mantém RLS e lógica
// de negócio centralizadas no backend, fora do alcance do navegador.
export const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
)
