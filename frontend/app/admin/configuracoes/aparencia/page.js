'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useAuth } from '../../../../hooks/useAuth'
import { getMe, atualizarMe } from '../../../../lib/api'
import { aplicarTema, CORES_DESTAQUE, MODOS, COR_PADRAO } from '../../../../lib/tema'

const TAMANHOS = [
  ['pequena', 'Pequena (14px)'],
  ['normal',  'Normal (16px)'],
  ['grande',  'Grande (18px)'],
]

export default function AparenciaPage() {
  const { token } = useAuth()
  const [loading,  setLoading]  = useState(true)
  const [salvando, setSalvando] = useState(false)
  const [msg,      setMsg]      = useState({ tipo: '', texto: '' })

  const [cor,             setCor]             = useState(COR_PADRAO)
  const [fonte,           setFonte]           = useState('normal')
  const [modo,            setModo]            = useState('claro')
  const [sidebarCompacta, setSidebarCompacta] = useState(false)

  useEffect(() => {
    if (!token) return
    async function init() {
      try {
        const me = await getMe(token)
        const p  = me.preferencias || {}
        setCor(p.cor_destaque || COR_PADRAO)
        setFonte(p.tamanho_fonte || 'normal')
        setModo(p.modo || 'claro')
        setSidebarCompacta(p.sidebar_compacta || false)
      } catch { /* layout trata */ }
      setLoading(false)
    }
    init()
  }, [token])

  // Pré-visualização ao vivo — só aplica quando a cor for um hex válido.
  useEffect(() => {
    if (!loading && /^#[0-9a-fA-F]{6}$/.test(cor)) {
      aplicarTema({ cor_destaque: cor, tamanho_fonte: fonte, modo })
    }
  }, [cor, fonte, modo, loading])

  async function salvar() {
    if (!/^#[0-9a-fA-F]{6}$/.test(cor)) {
      setMsg({ tipo: 'erro', texto: 'Cor inválida. Use o formato #rrggbb (ex: #3b82f6).' })
      return
    }
    setSalvando(true)
    setMsg({ tipo: '', texto: '' })
    try {
      const prefs = { cor_destaque: cor, tamanho_fonte: fonte, modo, sidebar_compacta: sidebarCompacta }
      await atualizarMe(token, { preferencias: prefs })
      aplicarTema(prefs)
      setMsg({ tipo: 'ok', texto: 'Aparência salva com sucesso!' })
    } catch (err) {
      setMsg({ tipo: 'erro', texto: err.message })
    }
    setSalvando(false)
  }

  if (loading) return <p style={{ color: 'var(--text-muted)' }}>Carregando...</p>

  return (
    <div className="max-w-2xl">
      <Link href="/admin/configuracoes" className="text-sm hover:underline" style={{ color: 'var(--text-muted)' }}>
        ‹ Voltar para Configurações
      </Link>
      <h1 className="text-2xl font-bold mt-2 mb-1" style={{ color: 'var(--text-primary)' }}>Aparência</h1>
      <p className="text-sm mb-6" style={{ color: 'var(--text-muted)' }}>
        Personalize o painel. As mudanças são aplicadas somente para a sua conta.
      </p>

      <div className="rounded-xl shadow-sm p-5 space-y-6" style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-color)' }}>

        {/* ── Modo ─────────────────────────────────────── */}
        <div>
          <p className="text-sm font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>Modo</p>
          <p className="text-xs mb-3" style={{ color: 'var(--text-muted)' }}>
            "Sistema" acompanha automaticamente o tema do seu SO.
          </p>
          <div className="flex gap-2">
            {MODOS.map(({ valor, label, icone }) => (
              <button key={valor} type="button" onClick={() => setModo(valor)}
                className="flex-1 flex flex-col items-center gap-1 py-3 rounded-lg border text-sm font-medium transition"
                style={modo === valor
                  ? { backgroundColor: 'var(--cor-destaque)', color: '#fff', borderColor: 'var(--cor-destaque)' }
                  : { borderColor: 'var(--border-color)', color: 'var(--text-muted)', backgroundColor: 'transparent' }}
              >
                <span className="text-xl">{icone}</span>
                <span>{label}</span>
              </button>
            ))}
          </div>
        </div>

        <hr style={{ borderColor: 'var(--border-color)' }} />

        {/* ── Cor de destaque ──────────────────────────── */}
        <div>
          <p className="text-sm font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>Cor de destaque</p>
          <p className="text-xs mb-3" style={{ color: 'var(--text-muted)' }}>
            Afeta a barra superior, itens ativos do menu e botões.
          </p>
          <div className="flex flex-wrap gap-3">
            {CORES_DESTAQUE.map(c => (
              <button key={c.valor} type="button" onClick={() => setCor(c.valor)}
                title={c.nome}
                className="w-10 h-10 rounded-full flex items-center justify-center transition"
                style={{
                  backgroundColor: c.valor,
                  outline: cor === c.valor ? '3px solid rgba(0,0,0,0.2)' : 'none',
                  outlineOffset: 2,
                  boxShadow: cor === c.valor ? `0 0 0 3px ${c.valor}40` : 'none',
                }}
              >
                {cor === c.valor && <span className="text-white text-lg leading-none">✓</span>}
              </button>
            ))}
          </div>

          {/* Campo hex livre */}
          <div className="flex items-center gap-3 mt-4">
            <div
              className="w-9 h-9 rounded-lg border flex-shrink-0"
              style={{ backgroundColor: cor, borderColor: 'var(--border-color)' }}
            />
            <input
              type="text"
              value={cor}
              placeholder="Ex: #3b82f6 — qualquer cor hexadecimal de 6 dígitos"
              maxLength={7}
              onChange={e => {
                const v = e.target.value
                setCor(v)
                // aplica preview só quando o hex estiver completo e válido
                if (/^#[0-9a-fA-F]{6}$/.test(v)) {
                  aplicarTema({ cor_destaque: v, tamanho_fonte: fonte, modo })
                }
              }}
              className="flex-1 text-sm font-mono rounded-lg px-3 py-2 border outline-none focus:ring-2"
              style={{
                backgroundColor: 'var(--bg-content)',
                borderColor: /^#[0-9a-fA-F]{6}$/.test(cor) ? 'var(--border-color)' : '#ef4444',
                color: 'var(--text-primary)',
                '--tw-ring-color': 'var(--cor-destaque)',
              }}
            />
            {!/^#[0-9a-fA-F]{6}$/.test(cor) && (
              <span className="text-xs text-red-500 whitespace-nowrap">Hex inválido</span>
            )}
          </div>
          <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
            Clique num círculo acima ou digite manualmente. Formato: <span className="font-mono">#rrggbb</span>
          </p>
        </div>

        <hr style={{ borderColor: 'var(--border-color)' }} />

        {/* ── Tamanho da fonte ─────────────────────────── */}
        <div>
          <p className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Tamanho da fonte</p>
          <div className="flex gap-2">
            {TAMANHOS.map(([k, label]) => (
              <button key={k} type="button" onClick={() => setFonte(k)}
                className="px-4 py-2 rounded-lg text-sm font-medium border transition"
                style={fonte === k
                  ? { backgroundColor: 'var(--cor-destaque)', color: '#fff', borderColor: 'var(--cor-destaque)' }
                  : { borderColor: 'var(--border-color)', color: 'var(--text-muted)', backgroundColor: 'transparent' }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <hr style={{ borderColor: 'var(--border-color)' }} />

        {/* ── Sidebar ──────────────────────────────────── */}
        <div>
          <p className="text-sm font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>Sidebar</p>
          <p className="text-xs mb-3" style={{ color: 'var(--text-muted)' }}>
            Iniciar com a sidebar recolhida para mais espaço de conteúdo.
          </p>
          <label className="flex items-center gap-3 cursor-pointer w-fit">
            <div className="relative">
              <input type="checkbox" className="sr-only" checked={sidebarCompacta}
                onChange={e => setSidebarCompacta(e.target.checked)} />
              <div
                className="w-10 h-6 rounded-full transition-colors duration-200"
                style={{ backgroundColor: sidebarCompacta ? 'var(--cor-destaque)' : 'var(--border-color)' }}
              />
              <div
                className="absolute top-1 w-4 h-4 bg-white rounded-full shadow transition-transform duration-200"
                style={{ transform: sidebarCompacta ? 'translateX(20px)' : 'translateX(4px)' }}
              />
            </div>
            <span className="text-sm" style={{ color: 'var(--text-primary)' }}>
              Iniciar com sidebar recolhida
            </span>
          </label>
        </div>

        <hr style={{ borderColor: 'var(--border-color)' }} />

        {/* ── Pré-visualização ─────────────────────────── */}
        <div>
          <p className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>Pré-visualização</p>
          <div className="rounded-lg overflow-hidden border" style={{ borderColor: 'var(--border-color)' }}>
            {/* mini navbar */}
            <div className="flex items-center gap-3 px-3 py-2 text-white text-xs" style={{ backgroundColor: 'var(--cor-destaque)' }}>
              <span className="font-semibold">GestãoAcademia</span>
              <span className="opacity-70">— Dashboard</span>
            </div>
            {/* mini content */}
            <div className="flex" style={{ backgroundColor: 'var(--bg-content)', minHeight: 64 }}>
              <div className="w-16 flex flex-col gap-1 p-2" style={{ backgroundColor: 'var(--bg-sidebar)' }}>
                <div className="h-2 rounded" style={{ backgroundColor: 'var(--cor-destaque)', width: '80%' }} />
                <div className="h-2 rounded opacity-40" style={{ backgroundColor: 'var(--nav-text)', width: '60%' }} />
                <div className="h-2 rounded opacity-40" style={{ backgroundColor: 'var(--nav-text)', width: '70%' }} />
              </div>
              <div className="flex-1 p-3 flex flex-col gap-2">
                <div className="h-3 rounded w-32" style={{ backgroundColor: 'var(--bg-card)', boxShadow: '0 1px 2px rgba(0,0,0,0.1)' }} />
                <div className="h-8 rounded" style={{ backgroundColor: 'var(--bg-card)', boxShadow: '0 1px 2px rgba(0,0,0,0.1)' }} />
              </div>
            </div>
          </div>
          <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
            A pré-visualização atualiza em tempo real conforme você altera as opções acima.
          </p>
        </div>

        {/* ── Ações ────────────────────────────────────── */}
        <div className="flex items-center gap-3">
          <button type="button" onClick={salvar} disabled={salvando}
            className="text-white px-5 py-2 rounded-lg text-sm font-medium transition disabled:opacity-60"
            style={{ backgroundColor: 'var(--cor-destaque)' }}>
            {salvando ? 'Salvando...' : 'Salvar aparência'}
          </button>
          {msg.texto && (
            <p className={`text-sm rounded-lg px-3 py-2 ${msg.tipo === 'erro' ? 'text-red-600 bg-red-50' : 'text-green-700 bg-green-50'}`}>
              {msg.texto}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
