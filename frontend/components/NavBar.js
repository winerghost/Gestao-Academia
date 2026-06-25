'use client'
import { useRouter } from 'next/navigation'
import { supabase } from '../lib/supabase'

export default function NavBar({ nomeAluno }) {
  const router = useRouter()

  async function logout() {
    await supabase.auth.signOut()
    router.replace('/login')
  }

  return (
    <nav className="bg-blue-600 text-white px-6 py-3 flex items-center justify-between shadow-md">
      <div className="flex items-center gap-2 font-semibold">
        <span className="text-xl">🏋️</span>
        <span>Portal do Aluno</span>
      </div>
      <div className="flex items-center gap-4">
        {nomeAluno && (
          <span className="text-sm text-blue-100 hidden sm:block">{nomeAluno}</span>
        )}
        <button
          onClick={logout}
          className="text-sm bg-white/20 hover:bg-white/30 px-3 py-1 rounded-lg transition"
        >
          Sair
        </button>
      </div>
    </nav>
  )
}
