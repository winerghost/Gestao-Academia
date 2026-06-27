'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { supabase } from '../../../../lib/supabase'
import { getMe, atualizarMe } from '../../../../lib/api'
import { aplicarTema, CORES_DESTAQUE, COR_PADRAO } from '../../../../lib/tema'

const TAMANHOS = [
  ['pequena', 'Pequena'],
  ['normal', 'Normal'],
  ['grande', 'Grande'],
]

export default function AparenciaPage() {
  const router = useRouter()
  const [token, setToken] = useState('')
  const [loading, setLoading] = useState(true)
  const [salvando, setSalvando] = useState(false)
  const [msg, setMsg] = useState({ tipo: '', texto: '' })

  const [cor, setCor] = useState(COR_PADRAO)
  const [fonte, setFonte] = useState('normal')

  useEffect(() => {
    async function init() {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) { router.replace('/login'); return }
      setToken(session.access_token)
      try {
        const me = await getMe(session.access_token)
        const p = me.preferencias || {}
        setCor(p.cor_destaque || COR_PADRAO)
        setFonte(p.tamanho_fonte || 'normal')
      } catch { /* layout trata */ }
      setLoading(false)
    }
    init()
  }, [router])

  // Pré-visualização ao vivo: aplica o tema enquanto o usuário escolhe.
  useEffect(() => {
    if (!loading) aplicarTema({ cor_destaque: cor, tamanho_fonte: fonte })
  }, [cor, fonte, loading])

  async function salvar() {
    setSalvando(true)
    setMsg({ tipo: '', texto: '' })
    try {
      await atualizarMe(token, { preferencias: { cor_destaque: cor, tamanho_fonte: fonte } })
      aplicarTema({ cor_destaque: cor, tamanho_fonte: fonte })
      setMsg({ tipo: 'ok', texto: 'Aparência salva.' })
    } catch (err) {
      setMsg({ tipo: 'erro', texto: err.message })
    }
    setSalvando(false)
  }

  if (loading) return <p className="text-gray-400">Carregando...</p>

  return (
    <div className="max-w-2xl">
      <Link href="/admin/configuracoes" className="text-sm text-gray-500 hover:text-gray-700">
        ‹ Voltar para Configurações
      </Link>
      <h1 className="text-2xl font-bold text-gray-800 mt-2 mb-1">Aparência</h1>
      <p className="text-sm text-gray-500 mb-6">
        Personalize o painel. As mudanças são aplicadas só para a sua conta.
      </p>

      <div className="bg-white rounded-xl shadow-sm p-5 space-y-6">
        {/* Cor de destaque */}
        <div>
          <p className="text-sm font-medium text-gray-700 mb-3">Cor de destaque</p>
          <div className="flex flex-wrap gap-3">
            {CORES_DESTAQUE.map(c => (
              <button key={c.valor} type="button" onClick={() => setCor(c.valor)}
                title={c.nome}
                className="w-10 h-10 rounded-full flex items-center justify-center transition"
                style={{
                  backgroundColor: c.valor,
                  outline: cor === c.valor ? '3px solid rgba(0,0,0,0.15)' : 'none',
                  outlineOffset: 2,
                }}
              >
                {cor === c.valor && <span className="text-white text-lg leading-none">✓</span>}
              </button>
            ))}
          </div>
        </div>

        <hr className="border-gray-100" />

        {/* Tamanho da fonte */}
        <div>
          <p className="text-sm font-medium text-gray-700 mb-3">Tamanho da fonte</p>
          <div className="flex gap-2">
            {TAMANHOS.map(([k, label]) => (
              <button key={k} type="button" onClick={() => setFonte(k)}
                className="px-4 py-2 rounded-lg text-sm font-medium border transition"
                style={fonte === k
                  ? { backgroundColor: 'var(--cor-destaque)', color: '#fff', borderColor: 'var(--cor-destaque)' }
                  : { borderColor: '#e5e7eb', color: '#6b7280' }}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <hr className="border-gray-100" />

        {/* Pré-visualização */}
        <div>
          <p className="text-sm font-medium text-gray-700 mb-3">Pré-visualização</p>
          <div className="rounded-lg border border-gray-100 p-4 flex items-center gap-3">
            <span className="px-4 py-2 rounded-lg text-white text-sm font-medium"
              style={{ backgroundColor: 'var(--cor-destaque)' }}>
              Botão de exemplo
            </span>
            <span className="text-sm" style={{ color: 'var(--cor-destaque)' }}>Texto destacado</span>
          </div>
        </div>

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
