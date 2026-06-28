'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '../lib/supabase'

// ─────────────────────────────────────────────────────────────────────────────
// useAuth — hook centralizado de autenticação
//
// Responsabilidades:
//   1. Lê a sessão do SDK do Supabase (memória local, sem request de rede).
//   2. Redireciona para /login se não houver sessão ativa.
//   3. Mantém o token atualizado via onAuthStateChange (logout em outra aba,
//      renovação automática de token).
//
// Uso em qualquer page/component que precise do access_token:
//
//   const { token, loading } = useAuth()
//   if (loading) return <p>Carregando...</p>
//   // token (string) está garantidamente disponível aqui
//
// Retorno:
//   token   — string JWT quando autenticado, null enquanto carrega ou após logout.
//   loading — true até o token ser confirmado (ou redirect ser iniciado).
// ─────────────────────────────────────────────────────────────────────────────
export function useAuth() {
  const router = useRouter()
  const [token,   setToken]   = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Flag de cleanup: impede setState após o componente desmontar.
    // Sem isso, o React emitiria warning de "memory leak" caso a Promise
    // de getSession resolvesse depois do unmount.
    let active = true

    // ── 1. Leitura inicial da sessão ──────────────────────────────────────
    // getSession() retorna a sessão em memória (ou do localStorage) sem
    // fazer nenhuma requisição HTTP ao Supabase — é instantâneo.
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (!active) return

      if (!session) {
        // Sem sessão: redireciona. Não define loading=false para que o
        // componente continue mostrando o spinner enquanto o redirect ocorre
        // (evita flash de conteúdo protegido antes da navegação).
        router.replace('/login')
        return
      }

      setToken(session.access_token)
      setLoading(false)
    })

    // ── 2. Escuta mudanças de sessão ──────────────────────────────────────
    // onAuthStateChange cobre cenários assíncronos que getSession não detecta:
    //   SIGNED_OUT      → logout em outra aba / token revogado no backend.
    //   TOKEN_REFRESHED → SDK renovou o access_token silenciosamente (expirou
    //                     mas o refresh_token ainda é válido). O novo token
    //                     deve ser usado nas próximas chamadas de API.
    //
    // INITIAL_SESSION é ignorado: getSession() acima já cobre a carga inicial
    // e evitamos double-setState desnecessário.
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (event, session) => {
        if (!active) return
        if (event === 'INITIAL_SESSION') return

        if (!session || event === 'SIGNED_OUT') {
          setToken(null)
          router.replace('/login')
          return
        }

        if (event === 'TOKEN_REFRESHED' && session.access_token) {
          // Atualiza o token em estado para que a próxima chamada de API
          // use o access_token renovado em vez do expirado.
          setToken(session.access_token)
        }
      }
    )

    // ── 3. Cleanup ────────────────────────────────────────────────────────
    // Cancela atualizações de estado e remove o listener de auth ao desmontar.
    return () => {
      active = false
      subscription.unsubscribe()
    }
  }, [router])

  return { token, loading }
}
