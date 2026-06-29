'use client'
import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useAuth } from '../../../hooks/useAuth'
import { getMe } from '../../../lib/api'

// Cada área vira um card. `adminOnly` esconde a área de quem não é admin
// (o backend também bloqueia, isto é só UX).
const AREAS = [
  {
    href: '/admin/configuracoes/conta',
    icon: '👤',
    titulo: 'Conta',
    descricao: 'Seus dados de acesso',
    itens: ['Perfil (nome e telefone)', 'Alterar senha'],
    adminOnly: false,
  },
  {
    href: '/admin/configuracoes/usuarios',
    icon: '🗂️',
    titulo: 'Usuários',
    descricao: 'Gerencie papéis e acessos',
    itens: ['Listar todos os usuários', 'Arrastar para alterar papel'],
    adminOnly: true,
  },
  {
    href: '/admin/configuracoes/academia',
    icon: '🏢',
    titulo: 'Academia',
    descricao: 'Dados do negócio',
    itens: ['Dados cadastrais', 'Horários de funcionamento'],
    adminOnly: true,
  },
  {
    href: '/admin/configuracoes/notificacoes',
    icon: '🔔',
    titulo: 'Notificações',
    descricao: 'E-mails de cobrança',
    itens: ['Lembrete de vencimento', 'Aviso de atraso'],
    adminOnly: true,
  },
  {
    href: '/admin/configuracoes/reset-senha',
    icon: '🔑',
    titulo: 'Redefinir Senha',
    descricao: 'Redefina a senha de qualquer usuário',
    itens: ['Localizar por nome ou e-mail', 'Definir nova senha sem precisar da atual'],
    adminOnly: true,
  },
  {
    href: '/admin/configuracoes/aparencia',
    icon: '🎨',
    titulo: 'Aparência',
    descricao: 'Personalize o painel',
    itens: ['Cor de destaque', 'Tamanho da fonte'],
    adminOnly: false,
  },
]

export default function ConfiguracoesPage() {
  const { token } = useAuth()
  const [tipo, setTipo] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busca, setBusca] = useState('')

  useEffect(() => {
    if (!token) return
    async function init() {
      try {
        const me = await getMe(token)
        setTipo(me.tipo)
      } catch { /* o layout já trata sessão inválida */ }
      setLoading(false)
    }
    init()
  }, [token])

  const areas = useMemo(() => {
    const termo = busca.trim().toLowerCase()
    return AREAS
      .filter(a => a.adminOnly ? tipo === 'admin' : true)
      .filter(a => {
        if (!termo) return true
        const alvo = [a.titulo, a.descricao, ...a.itens].join(' ').toLowerCase()
        return alvo.includes(termo)
      })
  }, [tipo, busca])

  if (loading) return <p className="text-gray-400">Carregando...</p>

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Configurações</h1>
        <p className="text-sm text-gray-500 mt-1">
          Escolha uma área para configurar. Use a busca para acessar direto.
        </p>
      </div>

      {/* Busca */}
      <div className="mb-6 max-w-md">
        <input
          value={busca}
          onChange={e => setBusca(e.target.value)}
          placeholder="🔎 Buscar configuração..."
          className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2"
          style={{ '--tw-ring-color': 'var(--cor-destaque)' }}
        />
      </div>

      {areas.length === 0 ? (
        <p className="text-center text-gray-400 py-12">Nenhuma configuração encontrada.</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {areas.map(area => (
            <Link
              key={area.href}
              href={area.href}
              className="group bg-white rounded-xl shadow-sm hover:shadow-md transition border border-transparent hover:border-gray-200 p-5 flex flex-col"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <span
                    className="w-10 h-10 rounded-lg flex items-center justify-center text-lg flex-shrink-0"
                    style={{ backgroundColor: 'color-mix(in srgb, var(--cor-destaque) 15%, white)' }}
                  >
                    {area.icon}
                  </span>
                  <div>
                    <h2 className="font-bold text-gray-800 leading-tight">{area.titulo}</h2>
                    <p className="text-xs text-gray-400">{area.descricao}</p>
                  </div>
                </div>
                <span
                  className="text-gray-300 group-hover:translate-x-1 transition-transform"
                  style={{ color: 'var(--cor-destaque)' }}
                >
                  ›
                </span>
              </div>
              <ul className="space-y-1 mt-1">
                {area.itens.map(item => (
                  <li key={item} className="text-sm text-gray-500 flex items-center gap-2">
                    <span className="text-gray-300">•</span> {item}
                  </li>
                ))}
              </ul>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
