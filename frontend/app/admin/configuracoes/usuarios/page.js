'use client'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '@/hooks/useAuth'
import {
  getMe, getUsuarios, atualizarTipoUsuario, atualizarStatusUsuario,
  criarUsuario, excluirUsuario,
} from '@/lib/api'
import CapturaFoto from '@/components/CapturaFoto'

const COLUNAS = [
  { tipo: 'admin',         label: 'Administrador', cor: '#ef4444', bg: '#fef2f2', icone: '👑' },
  { tipo: 'recepcionista', label: 'Recepcionista',  cor: '#3b82f6', bg: '#eff6ff', icone: '🖥️' },
  { tipo: 'instrutor',     label: 'Instrutor',      cor: '#10b981', bg: '#f0fdf4', icone: '💪' },
  { tipo: 'aluno',         label: 'Aluno',          cor: '#f59e0b', bg: '#fffbeb', icone: '🎓' },
]

const TIPOS_CRIACAO = [
  { value: 'admin',         label: 'Administrador' },
  { value: 'recepcionista', label: 'Recepcionista' },
  { value: 'instrutor',     label: 'Instrutor' },
]

const input = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2'
const ringStyle = { '--tw-ring-color': 'var(--cor-destaque)' }

function iniciais(nome) {
  return (nome || '?').split(' ').slice(0, 2).map(p => p[0]).join('').toUpperCase()
}

function cargoInfo(tipo) {
  return COLUNAS.find(c => c.tipo === tipo) || { label: tipo, cor: '#6b7280', bg: '#f3f4f6' }
}

function AvatarMini({ url, nome, cor }) {
  const [erro, setErro] = useState(false)
  if (url && !erro) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- avatar pequeno; next/image exigiria remotePatterns
      <img
        src={url}
        alt={nome}
        onError={() => setErro(true)}
        className="w-8 h-8 rounded-full object-cover flex-shrink-0"
      />
    )
  }
  return (
    <div
      className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
      style={{ backgroundColor: cor }}
    >
      {iniciais(nome)}
    </div>
  )
}

const FORM_VAZIO = { nome: '', email: '', senha: '', tipo: 'recepcionista', telefone: '', foto: null }

export default function UsuariosKanbanPage() {
  const router = useRouter()
  const { token } = useAuth()
  const [meId, setMeId]         = useState(null)
  const [usuarios, setUsuarios] = useState([])
  const [loading, setLoading]   = useState(true)
  const [erro, setErro]         = useState(null)
  const [toast, setToast]       = useState(null)
  const [dragOver, setDragOver] = useState(null)
  const [busca, setBusca]       = useState('')
  const [buscaDebounced, setBuscaDebounced] = useState('')
  const dragging = useRef(null)

  // Tabela
  const [aba, setAba]           = useState('membros')
  const [pageSize, setPageSize] = useState(20)
  const [page, setPage]         = useState(1)
  const [sortAsc, setSortAsc]   = useState(true)

  // Modal novo usuário
  const [modalAberto, setModalAberto]   = useState(false)
  const [novoForm, setNovoForm]         = useState(FORM_VAZIO)
  const [salvando, setSalvando]         = useState(false)
  const [erroModal, setErroModal]       = useState('')
  const [mostrarSenha, setMostrarSenha] = useState(false)

  // Confirmação de exclusão inline (guarda o id do usuário sendo confirmado)
  const [confirmandoId, setConfirmandoId] = useState(null)

  useEffect(() => {
    const t = setTimeout(() => setBuscaDebounced(busca), 400)
    return () => clearTimeout(t)
  }, [busca])

  const buscarUsuarios = useCallback(async (tok, termo) => {
    const params = termo ? { busca: termo } : {}
    const lista = await getUsuarios(tok, params)
    setUsuarios(lista)
  }, [])

  useEffect(() => {
    if (!token) return
    async function init() {
      try {
        const me = await getMe(token)
        if (me.tipo !== 'admin') { router.replace('/admin'); return }
        setMeId(me.id)
        await buscarUsuarios(token, '')
      } catch (e) {
        setErro(e.message)
      }
      setLoading(false)
    }
    init()
  }, [token, router, buscarUsuarios])

  useEffect(() => {
    if (token) buscarUsuarios(token, buscaDebounced)
  }, [buscaDebounced, token, buscarUsuarios])

  function showToast(msg, ok = true) {
    setToast({ msg, ok })
    setTimeout(() => setToast(null), 3500)
  }

  function porTipo(tipo) {
    return usuarios.filter(u => u.tipo === tipo && u.ativo !== false)
  }

  // ── Drag-and-drop (kanban) ───────────────────────────────────────────────

  function onDragStart(e, usuario) {
    dragging.current = usuario
    e.dataTransfer.effectAllowed = 'move'
  }

  function onDragOver(e, tipo) {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOver(tipo)
  }

  function onDragLeave() { setDragOver(null) }

  async function onDrop(e, novoTipo) {
    e.preventDefault()
    setDragOver(null)
    const u = dragging.current
    dragging.current = null
    if (!u || u.tipo === novoTipo) return

    if (u.id === meId) {
      showToast('Você não pode alterar seu próprio papel.', false)
      return
    }
    if (novoTipo === 'aluno') {
      showToast('Alunos devem ser cadastrados pelo formulário "Novo Aluno" (CPF obrigatório).', false)
      return
    }

    setUsuarios(prev => prev.map(x => x.id === u.id ? { ...x, tipo: novoTipo } : x))
    try {
      await atualizarTipoUsuario(token, u.id, novoTipo)
      showToast(`${u.nome} movido para ${COLUNAS.find(c => c.tipo === novoTipo)?.label}.`)
    } catch (err) {
      setUsuarios(prev => prev.map(x => x.id === u.id ? { ...x, tipo: u.tipo } : x))
      showToast(err.message || 'Erro ao atualizar papel.', false)
    }
  }

  // ── Troca de cargo via dropdown da tabela ───────────────────────────────

  async function mudarCargo(u, novoTipo) {
    if (novoTipo === u.tipo) return
    if (u.id === meId) { showToast('Você não pode alterar seu próprio papel.', false); return }
    if (novoTipo === 'aluno') {
      showToast('Alunos devem ser cadastrados pelo formulário "Novo Aluno" (CPF obrigatório).', false)
      return
    }
    const anterior = u.tipo
    setUsuarios(prev => prev.map(x => x.id === u.id ? { ...x, tipo: novoTipo } : x))
    try {
      await atualizarTipoUsuario(token, u.id, novoTipo)
      showToast(`${u.nome} agora é ${cargoInfo(novoTipo).label}.`)
    } catch (err) {
      setUsuarios(prev => prev.map(x => x.id === u.id ? { ...x, tipo: anterior } : x))
      showToast(err.message || 'Erro ao alterar cargo.', false)
    }
  }

  // ── Ativar/desativar ────────────────────────────────────────────────────

  async function toggleStatus(u) {
    if (u.id === meId) { showToast('Você não pode desativar sua própria conta.', false); return }
    const novo = !u.ativo
    setUsuarios(prev => prev.map(x => x.id === u.id ? { ...x, ativo: novo } : x))
    try {
      await atualizarStatusUsuario(token, u.id, novo)
      showToast(`${u.nome} foi ${novo ? 'ativado' : 'desativado'}.`)
    } catch (err) {
      setUsuarios(prev => prev.map(x => x.id === u.id ? { ...x, ativo: u.ativo } : x))
      showToast(err.message || 'Erro ao alterar status.', false)
    }
  }

  // ── Excluir usuário ──────────────────────────────────────────────────────

  async function excluirU(u) {
    setConfirmandoId(null)
    try {
      await excluirUsuario(token, u.id)
      setUsuarios(prev => prev.filter(x => x.id !== u.id))
      showToast(`${u.nome} foi excluído permanentemente.`)
    } catch (err) {
      showToast(err.message || 'Erro ao excluir usuário.', false)
    }
  }

  // ── Modal de criação ────────────────────────────────────────────────────

  function fecharModal() {
    setModalAberto(false)
    setNovoForm(FORM_VAZIO)
    setErroModal('')
    setMostrarSenha(false)
  }

  async function criarNovoUsuario(e) {
    e.preventDefault()
    setErroModal('')
    if (!novoForm.nome.trim()) { setErroModal('Nome obrigatório.'); return }
    if (!novoForm.email.trim()) { setErroModal('E-mail obrigatório.'); return }
    if (novoForm.senha.length < 6) { setErroModal('Senha deve ter ao menos 6 caracteres.'); return }

    setSalvando(true)
    try {
      const novo = await criarUsuario(token, {
        nome: novoForm.nome.trim(),
        email: novoForm.email.trim(),
        senha: novoForm.senha,
        tipo: novoForm.tipo,
        telefone: novoForm.telefone.trim() || null,
        foto: novoForm.foto || null,
      })
      setUsuarios(prev => [...prev, novo])
      showToast(`${novo.nome} criado como ${cargoInfo(novo.tipo).label}.`)
      fecharModal()
    } catch (err) {
      setErroModal(err.message || 'Erro ao criar usuário.')
    }
    setSalvando(false)
  }

  // ── Paginação / ordenação ────────────────────────────────────────────────

  const ordenados = [...usuarios].sort((a, b) => {
    const cmp = (a.nome || '').localeCompare(b.nome || '', 'pt-BR')
    return sortAsc ? cmp : -cmp
  })
  const totalPaginas = Math.max(1, Math.ceil(ordenados.length / pageSize))
  const paginaAtual  = Math.min(page, totalPaginas)
  const visiveis     = ordenados.slice((paginaAtual - 1) * pageSize, paginaAtual * pageSize)

  if (loading) return <p className="text-gray-400 p-6">Carregando...</p>
  if (erro)    return <p className="text-red-500 p-6">{erro}</p>

  return (
    <div>
      {/* ── Cabeçalho ──────────────────────────────────────────────────────── */}
      <div className="mb-6">
        <Link href="/admin/configuracoes" className="text-sm text-gray-400 hover:text-gray-600 mb-2 inline-block">
          ‹ Voltar para Configurações
        </Link>
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Usuários</h1>
            <p className="text-sm text-gray-500 mt-1">
              Arraste um usuário para a coluna do papel desejado.
            </p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <input
              type="text"
              placeholder="Buscar por nome ou e-mail..."
              value={busca}
              onChange={e => setBusca(e.target.value)}
              className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white w-full sm:w-64"
            />
            <button
              onClick={() => setModalAberto(true)}
              className="text-white px-4 py-2 rounded-lg text-sm font-semibold transition whitespace-nowrap"
              style={{ backgroundColor: 'var(--cor-destaque)' }}
            >
              + Novo usuário
            </button>
          </div>
        </div>
      </div>

      {/* ── Kanban ─────────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
        {COLUNAS.map(col => {
          const cards = porTipo(col.tipo)
          const isOver = dragOver === col.tipo
          return (
            <div
              key={col.tipo}
              onDragOver={e => onDragOver(e, col.tipo)}
              onDragLeave={onDragLeave}
              onDrop={e => onDrop(e, col.tipo)}
              style={{
                borderColor: isOver ? col.cor : 'transparent',
                borderWidth: 2,
                borderStyle: 'dashed',
                backgroundColor: isOver ? col.bg : '#f9fafb',
                transition: 'all 0.15s ease',
              }}
              className="rounded-xl p-3 min-h-[300px]"
            >
              <div className="flex items-center justify-between mb-3 px-1">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{col.icone}</span>
                  <span className="font-semibold text-gray-700 text-sm">{col.label}</span>
                </div>
                <span
                  className="text-xs font-bold px-2 py-0.5 rounded-full"
                  style={{ backgroundColor: col.bg, color: col.cor, border: `1px solid ${col.cor}33` }}
                >
                  {cards.length}
                </span>
              </div>

              <div className="h-1 rounded-full mb-3" style={{ backgroundColor: col.cor }} />

              <div className="space-y-2">
                {cards.length === 0 && (
                  <p className="text-xs text-gray-400 text-center py-6 select-none">
                    Nenhum usuário
                  </p>
                )}
                {cards.map(u => {
                  const isMe = u.id === meId
                  return (
                    <div
                      key={u.id}
                      draggable={!isMe}
                      onDragStart={e => onDragStart(e, u)}
                      className="bg-white rounded-lg p-3 shadow-sm border border-gray-100 select-none"
                      style={{ cursor: isMe ? 'not-allowed' : 'grab', opacity: isMe ? 0.7 : 1 }}
                      title={isMe ? 'Você não pode mover sua própria conta' : `Arraste para alterar o papel de ${u.nome}`}
                    >
                      <div className="flex items-center gap-2">
                        <AvatarMini url={u.avatar_url} nome={u.nome} cor={col.cor} />
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-gray-800 truncate leading-tight">
                            {u.nome}
                            {isMe && <span className="ml-1 text-xs text-gray-400">(você)</span>}
                          </p>
                          <p className="text-xs text-gray-400 truncate">{u.email}</p>
                        </div>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )
        })}
      </div>

      {/* ── Tabela "Equipe" ─────────────────────────────────────────────────── */}
      <div className="mt-10">
        <h2 className="text-xl font-bold text-gray-800">Equipe</h2>
        <p className="text-sm text-gray-500 mt-1">
          Gerencie os membros da sua equipe e seus cargos.
        </p>

        <div className="flex gap-1 mt-4 bg-gray-100 rounded-full p-1 w-fit">
          {[
            { id: 'membros', label: `Membros (${usuarios.length})` },
            { id: 'cargos',  label: `Cargos (${COLUNAS.length})` },
          ].map(t => (
            <button
              key={t.id}
              onClick={() => setAba(t.id)}
              className="px-4 py-1.5 rounded-full text-sm font-medium transition"
              style={
                aba === t.id
                  ? { backgroundColor: 'white', color: '#111827', boxShadow: '0 1px 2px rgba(0,0,0,0.08)' }
                  : { color: '#6b7280' }
              }
            >
              {t.label}
            </button>
          ))}
        </div>

        {aba === 'cargos' ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mt-5">
            {COLUNAS.map(col => (
              <div key={col.tipo} className="bg-white rounded-xl border border-gray-100 p-4">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-lg">{col.icone}</span>
                  <span className="font-semibold text-gray-700 text-sm">{col.label}</span>
                </div>
                <p className="text-2xl font-bold" style={{ color: col.cor }}>
                  {porTipo(col.tipo).length}
                </p>
                <p className="text-xs text-gray-400">
                  {porTipo(col.tipo).length === 1 ? 'membro' : 'membros'}
                </p>
              </div>
            ))}
          </div>
        ) : (
          <>
            <div className="flex items-center gap-2 text-sm text-gray-500 mt-5 mb-3">
              <span>{usuarios.length} {usuarios.length === 1 ? 'registro' : 'registros'}</span>
              <span className="text-gray-300">|</span>
              <span>Exibir</span>
              <select
                value={pageSize}
                onChange={e => { setPageSize(Number(e.target.value)); setPage(1) }}
                className="border border-gray-200 rounded-lg px-2 py-1 bg-white focus:outline-none focus:ring-2"
                style={ringStyle}
              >
                {[10, 20, 50].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
              <span>por página</span>
            </div>

            <div className="bg-white rounded-xl border border-gray-100 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 text-gray-500 text-xs uppercase">
                      <th className="text-left font-semibold px-4 py-3">
                        <button
                          onClick={() => setSortAsc(s => !s)}
                          className="inline-flex items-center gap-1 hover:text-gray-700"
                        >
                          Nome <span className="text-gray-400">{sortAsc ? '▲' : '▼'}</span>
                        </button>
                      </th>
                      <th className="text-left font-semibold px-4 py-3">E-mail</th>
                      <th className="text-left font-semibold px-4 py-3">Cargo</th>
                      <th className="text-center font-semibold px-4 py-3">Status</th>
                      <th className="text-right font-semibold px-4 py-3">Ações</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visiveis.map(u => {
                      const isMe = u.id === meId
                      const info = cargoInfo(u.tipo)
                      const confirmando = confirmandoId === u.id
                      return (
                        <tr key={u.id} className="border-t border-gray-100 hover:bg-gray-50/60">
                          {/* Nome + avatar */}
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <AvatarMini url={u.avatar_url} nome={u.nome} cor={info.cor} />
                              <span className="font-medium text-gray-800">
                                {u.nome}
                                {isMe && (
                                  <span className="ml-1.5 text-xs text-gray-500 bg-gray-100 rounded-full px-2 py-0.5">
                                    você
                                  </span>
                                )}
                              </span>
                            </div>
                          </td>
                          {/* E-mail */}
                          <td className="px-4 py-3 text-gray-500">{u.email}</td>
                          {/* Cargo */}
                          <td className="px-4 py-3">
                            {isMe ? (
                              <span
                                className="inline-block text-xs font-semibold rounded-full px-3 py-1"
                                style={{ backgroundColor: '#f5f3ff', color: '#7c3aed', border: '1px solid #ddd6fe' }}
                              >
                                Dono
                              </span>
                            ) : (
                              <select
                                value={u.tipo}
                                onChange={e => mudarCargo(u, e.target.value)}
                                className="border border-gray-200 rounded-lg px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 cursor-pointer"
                                style={ringStyle}
                              >
                                {COLUNAS.map(c => (
                                  <option key={c.tipo} value={c.tipo}>{c.label}</option>
                                ))}
                              </select>
                            )}
                          </td>
                          {/* Status */}
                          <td className="px-4 py-3 text-center">
                            <span
                              className="inline-block text-xs font-semibold rounded-full px-3 py-1"
                              style={
                                u.ativo
                                  ? { backgroundColor: '#f0fdf4', color: '#16a34a' }
                                  : { backgroundColor: '#fef2f2', color: '#dc2626' }
                              }
                            >
                              {u.ativo ? 'Ativo' : 'Inativo'}
                            </span>
                          </td>
                          {/* Ações */}
                          <td className="px-4 py-3 text-right">
                            {isMe ? (
                              <span className="text-gray-300">—</span>
                            ) : confirmando ? (
                              <span className="inline-flex items-center gap-2">
                                <span className="text-xs text-gray-600">Excluir definitivamente?</span>
                                <button
                                  onClick={() => excluirU(u)}
                                  className="text-xs font-semibold text-red-600 hover:underline"
                                >
                                  Sim
                                </button>
                                <button
                                  onClick={() => setConfirmandoId(null)}
                                  className="text-xs text-gray-500 hover:underline"
                                >
                                  Não
                                </button>
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-4">
                                <button
                                  onClick={() => toggleStatus(u)}
                                  className="text-sm font-medium hover:underline whitespace-nowrap"
                                  style={{ color: u.ativo ? '#dc2626' : '#16a34a' }}
                                >
                                  {u.ativo ? '⊘ Desativar' : '⏻ Ativar'}
                                </button>
                                <button
                                  onClick={() => setConfirmandoId(u.id)}
                                  className="text-sm font-medium text-red-500 hover:text-red-700 hover:underline"
                                >
                                  Excluir
                                </button>
                              </span>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                    {visiveis.length === 0 && (
                      <tr>
                        <td colSpan={5} className="text-center text-gray-400 py-8">
                          Nenhum usuário.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {totalPaginas > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 text-sm text-gray-500">
                  <span>Página {paginaAtual} de {totalPaginas}</span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={paginaAtual === 1}
                      className="px-3 py-1 rounded-lg border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
                    >
                      Anterior
                    </button>
                    <button
                      onClick={() => setPage(p => Math.min(totalPaginas, p + 1))}
                      disabled={paginaAtual === totalPaginas}
                      className="px-3 py-1 rounded-lg border border-gray-200 disabled:opacity-40 hover:bg-gray-50"
                    >
                      Próxima
                    </button>
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* ── Modal: Novo usuário ─────────────────────────────────────────────── */}
      {modalAberto && (
        <div
          className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center p-4"
          onClick={e => { if (e.target === e.currentTarget) fecharModal() }}
        >
          <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-5">
                <h2 className="text-lg font-bold text-gray-800">Novo usuário</h2>
                <button
                  onClick={fecharModal}
                  className="text-gray-400 hover:text-gray-600 text-xl leading-none"
                  aria-label="Fechar"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={criarNovoUsuario}>
                {/* Foto */}
                <div className="mb-5">
                  <label className="text-xs font-medium text-gray-500 mb-2 block">
                    Foto (opcional)
                  </label>
                  <CapturaFoto
                    value={novoForm.foto}
                    onChange={d => setNovoForm(f => ({ ...f, foto: d }))}
                    nome={novoForm.nome}
                    disabled={salvando}
                  />
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {/* Nome */}
                  <div className="sm:col-span-2">
                    <label className="text-xs text-gray-500 mb-1 block">Nome completo *</label>
                    <input
                      className={input}
                      style={ringStyle}
                      required
                      placeholder="João da Silva"
                      value={novoForm.nome}
                      onChange={e => setNovoForm(f => ({ ...f, nome: e.target.value }))}
                      disabled={salvando}
                    />
                  </div>

                  {/* E-mail */}
                  <div>
                    <label className="text-xs text-gray-500 mb-1 block">E-mail *</label>
                    <input
                      type="email"
                      className={input}
                      style={ringStyle}
                      required
                      placeholder="joao@academia.com"
                      value={novoForm.email}
                      onChange={e => setNovoForm(f => ({ ...f, email: e.target.value }))}
                      disabled={salvando}
                    />
                  </div>

                  {/* Tipo */}
                  <div>
                    <label className="text-xs text-gray-500 mb-1 block">Tipo *</label>
                    <select
                      className={input}
                      style={ringStyle}
                      value={novoForm.tipo}
                      onChange={e => setNovoForm(f => ({ ...f, tipo: e.target.value }))}
                      disabled={salvando}
                    >
                      {TIPOS_CRIACAO.map(t => (
                        <option key={t.value} value={t.value}>{t.label}</option>
                      ))}
                    </select>
                  </div>

                  {/* Senha */}
                  <div className="sm:col-span-2">
                    <label className="text-xs text-gray-500 mb-1 block">Senha inicial *</label>
                    <div className="relative">
                      <input
                        type={mostrarSenha ? 'text' : 'password'}
                        className={input}
                        style={ringStyle}
                        required
                        minLength={6}
                        placeholder="Mínimo 6 caracteres"
                        value={novoForm.senha}
                        onChange={e => setNovoForm(f => ({ ...f, senha: e.target.value }))}
                        disabled={salvando}
                      />
                      <button
                        type="button"
                        onClick={() => setMostrarSenha(s => !s)}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-xs"
                      >
                        {mostrarSenha ? 'Ocultar' : 'Mostrar'}
                      </button>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      Comunique a senha ao usuário para o primeiro acesso.
                    </p>
                  </div>

                  {/* Telefone */}
                  <div className="sm:col-span-2">
                    <label className="text-xs text-gray-500 mb-1 block">Telefone</label>
                    <input
                      className={input}
                      style={ringStyle}
                      placeholder="(11) 99999-9999"
                      value={novoForm.telefone}
                      onChange={e => setNovoForm(f => ({ ...f, telefone: e.target.value }))}
                      disabled={salvando}
                    />
                  </div>
                </div>

                {erroModal && (
                  <p className="text-sm text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2 mt-4">
                    {erroModal}
                  </p>
                )}

                <div className="flex gap-3 mt-5">
                  <button
                    type="submit"
                    disabled={salvando}
                    className="text-white px-5 py-2 rounded-lg text-sm font-semibold transition disabled:opacity-60"
                    style={{ backgroundColor: 'var(--cor-destaque)' }}
                  >
                    {salvando ? 'Criando...' : 'Criar usuário'}
                  </button>
                  <button
                    type="button"
                    onClick={fecharModal}
                    disabled={salvando}
                    className="px-5 py-2 rounded-lg text-sm font-medium border border-gray-200 text-gray-600 hover:bg-gray-50 transition disabled:opacity-60"
                  >
                    Cancelar
                  </button>
                </div>

                <p className="text-xs text-gray-400 mt-4">
                  Para cadastrar alunos (CPF obrigatório), use a{' '}
                  <Link href="/admin/alunos" className="underline hover:text-gray-600" onClick={fecharModal}>
                    tela de Alunos
                  </Link>.
                </p>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* ── Toast ───────────────────────────────────────────────────────────── */}
      {toast && (
        <div
          className="fixed bottom-6 left-1/2 -translate-x-1/2 px-5 py-3 rounded-xl shadow-lg text-sm font-medium text-white z-50 transition-all max-w-sm text-center"
          style={{ backgroundColor: toast.ok ? '#10b981' : '#ef4444' }}
        >
          {toast.msg}
        </div>
      )}
    </div>
  )
}
