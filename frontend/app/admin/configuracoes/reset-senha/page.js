'use client'
import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/hooks/useAuth'
import { getMe, getUsuarios, resetSenhaUsuario } from '@/lib/api'

const TIPO_BADGE = {
  admin:         'bg-red-50 text-red-600',
  recepcionista: 'bg-blue-50 text-blue-600',
  instrutor:     'bg-green-50 text-green-700',
  aluno:         'bg-yellow-50 text-yellow-700',
}
const TIPO_LABEL = {
  admin: 'Administrador', recepcionista: 'Recepcionista',
  instrutor: 'Instrutor', aluno: 'Aluno',
}

const CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789@#$!'
function gerarSenha() {
  return Array.from({ length: 12 }, () => CHARS[Math.floor(Math.random() * CHARS.length)]).join('')
}

function iniciais(nome = '') {
  return nome.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase() || '?'
}

function AvatarMini({ url, nome, cor = '#6b7280' }) {
  const [erro, setErro] = useState(false)
  if (url && !erro) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img src={url} alt={nome} onError={() => setErro(true)}
        className="w-10 h-10 rounded-full object-cover flex-shrink-0" />
    )
  }
  return (
    <div className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold text-white flex-shrink-0"
      style={{ backgroundColor: cor }}>
      {iniciais(nome)}
    </div>
  )
}

const input = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-orange-400'

export default function ResetSenhaPage() {
  const router = useRouter()
  const { token } = useAuth()
  const [meId, setMeId] = useState(null)
  const [loading, setLoading] = useState(true)

  // Busca
  const [busca, setBusca] = useState('')
  const [resultados, setResultados] = useState([])
  const [buscando, setBuscando] = useState(false)
  const [aberto, setAberto] = useState(false)
  const debounceRef = useRef(null)
  const wrapperRef = useRef(null)

  // Usuário selecionado
  const [selecionado, setSelecionado] = useState(null)

  // Formulário de senha
  const [senhaNova, setSenhaNova] = useState('')
  const [confirmar, setConfirmar] = useState('')
  const [mostrar, setMostrar] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const [toast, setToast] = useState(null)

  function exibirToast(msg, ok = true) {
    setToast({ msg, ok })
    setTimeout(() => setToast(null), 4500)
  }

  // Verifica acesso admin
  useEffect(() => {
    if (!token) return
    async function init() {
      try {
        const me = await getMe(token)
        if (me.tipo !== 'admin') { router.replace('/admin'); return }
        setMeId(me.id)
      } catch { router.replace('/admin') }
      setLoading(false)
    }
    init()
  }, [token, router])

  // Debounce da busca
  useEffect(() => {
    if (!busca.trim()) { setResultados([]); setAberto(false); return }
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(async () => {
      setBuscando(true)
      try {
        const lista = await getUsuarios(token, { busca: busca.trim() })
        setResultados(lista.slice(0, 8))
        setAberto(true)
      } catch { setResultados([]) }
      setBuscando(false)
    }, 350)
    return () => clearTimeout(debounceRef.current)
  }, [busca, token])

  // Fecha dropdown ao clicar fora
  useEffect(() => {
    function handler(e) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) setAberto(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  function selecionar(u) {
    setSelecionado(u)
    setBusca('')
    setResultados([])
    setAberto(false)
    setSenhaNova('')
    setConfirmar('')
    setMostrar(false)
  }

  function limparSelecao() {
    setSelecionado(null)
    setSenhaNova('')
    setConfirmar('')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!selecionado) return
    if (senhaNova.length < 6) {
      exibirToast('A senha deve ter ao menos 6 caracteres.', false); return
    }
    if (senhaNova !== confirmar) {
      exibirToast('As senhas não conferem.', false); return
    }
    setSalvando(true)
    try {
      await resetSenhaUsuario(token, selecionado.id, senhaNova)
      exibirToast(`Senha de ${selecionado.nome} redefinida com sucesso.`)
      setSenhaNova('')
      setConfirmar('')
      setMostrar(false)
    } catch (err) {
      exibirToast(err.message || 'Erro ao redefinir senha.', false)
    }
    setSalvando(false)
  }

  function usarSenhaAleatoria() {
    const nova = gerarSenha()
    setSenhaNova(nova)
    setConfirmar(nova)
    setMostrar(true)
  }

  if (loading) {
    return (
      <div className="flex justify-center py-16">
        <div className="w-5 h-5 border-2 border-orange-200 border-t-orange-500 rounded-full animate-spin" />
      </div>
    )
  }

  const ehProprioAdmin = selecionado?.id === meId

  return (
    <div className="max-w-xl">
      {/* Cabeçalho */}
      <Link href="/admin/configuracoes" className="text-sm text-gray-400 hover:text-gray-600 inline-block mb-3">
        ‹ Voltar para Configurações
      </Link>
      <h1 className="text-2xl font-bold text-gray-800 mb-1">Redefinir Senha</h1>
      <p className="text-sm text-gray-400 mb-8">
        Localize o usuário e defina uma nova senha. Exclusivo para administradores.
      </p>

      {/* Toast */}
      {toast && (
        <div className={`mb-5 px-4 py-3 rounded-lg text-sm font-medium ${
          toast.ok ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
        }`}>
          {toast.msg}
        </div>
      )}

      {/* Busca */}
      <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5 mb-4">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">1. Localizar usuário</h2>

        <div ref={wrapperRef} className="relative">
          <div className="relative">
            <input
              type="text"
              value={busca}
              onChange={e => { setBusca(e.target.value); setSelecionado(null) }}
              placeholder="Buscar por nome ou e-mail..."
              className={input}
              autoComplete="off"
            />
            {buscando && (
              <div className="absolute right-3 top-1/2 -translate-y-1/2">
                <div className="w-4 h-4 border-2 border-orange-200 border-t-orange-500 rounded-full animate-spin" />
              </div>
            )}
          </div>

          {/* Dropdown de resultados */}
          {aberto && resultados.length > 0 && (
            <div className="absolute z-20 mt-1 w-full bg-white border border-gray-100 rounded-xl shadow-lg overflow-hidden">
              {resultados.map(u => (
                <button
                  key={u.id}
                  type="button"
                  onClick={() => selecionar(u)}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 transition-colors text-left border-b border-gray-50 last:border-0"
                >
                  <AvatarMini url={u.avatar_url} nome={u.nome} />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">{u.nome}</p>
                    <p className="text-xs text-gray-400 truncate">{u.email}</p>
                  </div>
                  <span className={`ml-auto flex-shrink-0 text-xs font-semibold px-2 py-0.5 rounded-full ${TIPO_BADGE[u.tipo] ?? 'bg-gray-100 text-gray-500'}`}>
                    {TIPO_LABEL[u.tipo] ?? u.tipo}
                  </span>
                </button>
              ))}
            </div>
          )}

          {aberto && resultados.length === 0 && !buscando && busca.trim() && (
            <div className="absolute z-20 mt-1 w-full bg-white border border-gray-100 rounded-xl shadow-lg px-4 py-3 text-sm text-gray-400">
              Nenhum usuário encontrado para "{busca}".
            </div>
          )}
        </div>

        {/* Card do usuário selecionado */}
        {selecionado && (
          <div className="mt-4 flex items-center gap-3 p-3 rounded-lg bg-gray-50 border border-gray-100">
            <AvatarMini url={selecionado.avatar_url} nome={selecionado.nome} />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-gray-800">{selecionado.nome}</p>
              <p className="text-xs text-gray-400">{selecionado.email}</p>
            </div>
            <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${TIPO_BADGE[selecionado.tipo] ?? 'bg-gray-100 text-gray-500'}`}>
              {TIPO_LABEL[selecionado.tipo] ?? selecionado.tipo}
            </span>
            <button
              type="button"
              onClick={limparSelecao}
              className="ml-1 text-gray-300 hover:text-gray-500 transition text-lg leading-none flex-shrink-0"
              title="Trocar usuário"
            >
              ✕
            </button>
          </div>
        )}
      </div>

      {/* Formulário de senha */}
      {selecionado && (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">2. Definir nova senha</h2>

          {ehProprioAdmin ? (
            <div className="text-sm text-amber-700 bg-amber-50 rounded-lg px-4 py-3 border border-amber-100">
              Para alterar sua própria senha, acesse{' '}
              <Link href="/admin/configuracoes/conta" className="font-semibold underline hover:text-amber-900">
                Conta
              </Link>.
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Nova senha */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs text-gray-500">Nova senha *</label>
                  <button
                    type="button"
                    onClick={usarSenhaAleatoria}
                    className="text-xs text-orange-500 hover:text-orange-700 font-medium transition"
                  >
                    Gerar senha aleatória
                  </button>
                </div>
                <div className="relative">
                  <input
                    type={mostrar ? 'text' : 'password'}
                    value={senhaNova}
                    onChange={e => setSenhaNova(e.target.value)}
                    required
                    minLength={6}
                    placeholder="Mínimo 6 caracteres"
                    className={input + ' pr-20'}
                    disabled={salvando}
                  />
                  <button
                    type="button"
                    onClick={() => setMostrar(s => !s)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-gray-400 hover:text-gray-600 transition"
                  >
                    {mostrar ? 'Ocultar' : 'Mostrar'}
                  </button>
                </div>
              </div>

              {/* Confirmar */}
              <div>
                <label className="text-xs text-gray-500 mb-1 block">Confirmar senha *</label>
                <input
                  type={mostrar ? 'text' : 'password'}
                  value={confirmar}
                  onChange={e => setConfirmar(e.target.value)}
                  required
                  minLength={6}
                  placeholder="Repita a nova senha"
                  className={input}
                  disabled={salvando}
                />
                {confirmar && senhaNova !== confirmar && (
                  <p className="text-xs text-red-500 mt-1">As senhas não conferem.</p>
                )}
              </div>

              <p className="text-xs text-gray-400">
                O usuário deverá usar esta senha no próximo acesso. Comunique-a de forma segura.
              </p>

              <button
                type="submit"
                disabled={salvando || !senhaNova || senhaNova !== confirmar}
                className="w-full bg-orange-500 hover:bg-orange-600 disabled:opacity-50 text-white py-2.5 rounded-lg text-sm font-semibold transition"
              >
                {salvando ? 'Redefinindo...' : 'Redefinir senha'}
              </button>
            </form>
          )}
        </div>
      )}
    </div>
  )
}
