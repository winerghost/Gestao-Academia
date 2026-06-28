'use client'
import { useState, useEffect } from 'react'
import { useAuth } from '../../hooks/useAuth'
import { getPortalFrequencias } from '../../lib/api'
import NavBar from '../../components/NavBar'

export default function Frequencia() {
  const { token } = useAuth()
  const [frequencias, setFrequencias] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) return
    async function carregar() {
      try {
        const dados = await getPortalFrequencias(token)
        setFrequencias(dados)
      } finally {
        setLoading(false)
      }
    }
    carregar()
  }, [token])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-400">
        Carregando...
      </div>
    )
  }

  return (
    <div className="min-h-screen">
      <NavBar />
      <main className="max-w-2xl mx-auto px-4 py-8">
        <div className="flex items-center gap-3 mb-6">
          <a href="/" className="text-sm text-blue-600 hover:underline">← Voltar</a>
          <h1 className="text-lg font-bold text-gray-800">Histórico de Frequência</h1>
        </div>

        {frequencias.length === 0 ? (
          <p className="text-center text-gray-400 py-12">Nenhuma frequência registrada.</p>
        ) : (
          <div className="bg-white rounded-2xl shadow-sm divide-y divide-gray-50">
            {frequencias.map(f => {
              const dt = new Date(f.data_hora)
              return (
                <div key={f.id} className="px-5 py-3.5 flex justify-between items-center">
                  <span className="text-sm text-gray-700 capitalize">
                    {dt.toLocaleDateString('pt-BR', {
                      weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
                    })}
                  </span>
                  <span className="text-xs text-gray-400 tabular-nums">
                    {dt.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              )
            })}
          </div>
        )}
      </main>
    </div>
  )
}
