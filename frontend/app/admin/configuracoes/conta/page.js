'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { supabase } from '../../../../lib/supabase'
import { getMe, atualizarMe, trocarSenha } from '../../../../lib/api'

const input = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2'
const ring = { '--tw-ring-color': 'var(--cor-destaque)' }
const btn = 'text-white px-5 py-2 rounded-lg text-sm font-medium transition disabled:opacity-60'
const btnStyle = { backgroundColor: 'var(--cor-destaque)' }

function Aviso({ tipo, children }) {
  if (!children) return null
  const cor = tipo === 'erro'
    ? 'text-red-600 bg-red-50'
    : 'text-green-700 bg-green-50'
  return <p className={`text-sm rounded-lg px-3 py-2 ${cor}`}>{children}</p>
}

export default function ContaPage() {
  const router = useRouter()
  const [token, setToken] = useState('')
  const [loading, setLoading] = useState(true)

  // Perfil
  const [perfil, setPerfil] = useState({ nome: '', telefone: '' })
  const [salvandoPerfil, setSalvandoPerfil] = useState(false)
  const [msgPerfil, setMsgPerfil] = useState({ tipo: '', texto: '' })

  // Senha
  const [senha, setSenha] = useState({ senha_atual: '', senha_nova: '', confirmar: '' })
  const [salvandoSenha, setSalvandoSenha] = useState(false)
  const [msgSenha, setMsgSenha] = useState({ tipo: '', texto: '' })

  useEffect(() => {
    async function init() {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) { router.replace('/login'); return }
      setToken(session.access_token)
      try {
        const me = await getMe(session.access_token)
        setPerfil({ nome: me.nome || '', telefone: me.telefone || '' })
      } catch { /* layout trata */ }
      setLoading(false)
    }
    init()
  }, [router])

  async function salvarPerfil(e) {
    e.preventDefault()
    setSalvandoPerfil(true)
    setMsgPerfil({ tipo: '', texto: '' })
    try {
      await atualizarMe(token, { nome: perfil.nome, telefone: perfil.telefone })
      setMsgPerfil({ tipo: 'ok', texto: 'Perfil atualizado com sucesso.' })
    } catch (err) {
      setMsgPerfil({ tipo: 'erro', texto: err.message })
    }
    setSalvandoPerfil(false)
  }

  async function salvarSenha(e) {
    e.preventDefault()
    setMsgSenha({ tipo: '', texto: '' })
    if (senha.senha_nova !== senha.confirmar) {
      setMsgSenha({ tipo: 'erro', texto: 'A confirmação não confere com a nova senha.' })
      return
    }
    if (senha.senha_nova.length < 6) {
      setMsgSenha({ tipo: 'erro', texto: 'A nova senha deve ter ao menos 6 caracteres.' })
      return
    }
    setSalvandoSenha(true)
    try {
      await trocarSenha(token, { senha_atual: senha.senha_atual, senha_nova: senha.senha_nova })
      setMsgSenha({ tipo: 'ok', texto: 'Senha alterada com sucesso.' })
      setSenha({ senha_atual: '', senha_nova: '', confirmar: '' })
    } catch (err) {
      setMsgSenha({ tipo: 'erro', texto: err.message })
    }
    setSalvandoSenha(false)
  }

  if (loading) return <p className="text-gray-400">Carregando...</p>

  return (
    <div className="max-w-2xl">
      <Link href="/admin/configuracoes" className="text-sm text-gray-500 hover:text-gray-700">
        ‹ Voltar para Configurações
      </Link>
      <h1 className="text-2xl font-bold text-gray-800 mt-2 mb-6">Conta</h1>

      {/* Perfil */}
      <div className="bg-white rounded-xl shadow-sm p-5 mb-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Perfil</h2>
        <form onSubmit={salvarPerfil} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <label className="text-xs text-gray-500 mb-1 block">Nome *</label>
            <input className={input} style={ring} required placeholder="Seu nome completo" value={perfil.nome}
              onChange={e => setPerfil(p => ({ ...p, nome: e.target.value }))} />
          </div>
          <div className="sm:col-span-2">
            <label className="text-xs text-gray-500 mb-1 block">Telefone</label>
            <input className={input} style={ring} value={perfil.telefone}
              placeholder="(11) 99999-9999"
              onChange={e => setPerfil(p => ({ ...p, telefone: e.target.value }))} />
          </div>
          <div className="sm:col-span-2 flex items-center gap-3">
            <button type="submit" className={btn} style={btnStyle} disabled={salvandoPerfil}>
              {salvandoPerfil ? 'Salvando...' : 'Salvar perfil'}
            </button>
            <Aviso tipo={msgPerfil.tipo}>{msgPerfil.texto}</Aviso>
          </div>
        </form>
      </div>

      {/* Senha */}
      <div className="bg-white rounded-xl shadow-sm p-5">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Alterar senha</h2>
        <form onSubmit={salvarSenha} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <label className="text-xs text-gray-500 mb-1 block">Senha atual *</label>
            <input type="password" className={input} style={ring} required placeholder="Digite sua senha atual" value={senha.senha_atual}
              onChange={e => setSenha(s => ({ ...s, senha_atual: e.target.value }))} />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Nova senha *</label>
            <input type="password" className={input} style={ring} required placeholder="Mínimo 6 caracteres" value={senha.senha_nova}
              onChange={e => setSenha(s => ({ ...s, senha_nova: e.target.value }))} />
          </div>
          <div>
            <label className="text-xs text-gray-500 mb-1 block">Confirmar nova senha *</label>
            <input type="password" className={input} style={ring} required placeholder="Repita a nova senha" value={senha.confirmar}
              onChange={e => setSenha(s => ({ ...s, confirmar: e.target.value }))} />
          </div>
          <div className="sm:col-span-2 flex items-center gap-3">
            <button type="submit" className={btn} style={btnStyle} disabled={salvandoSenha}>
              {salvandoSenha ? 'Alterando...' : 'Alterar senha'}
            </button>
            <Aviso tipo={msgSenha.tipo}>{msgSenha.texto}</Aviso>
          </div>
        </form>
      </div>
    </div>
  )
}
