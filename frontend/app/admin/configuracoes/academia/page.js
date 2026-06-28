'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useAuth } from '../../../../hooks/useAuth'
import { getConfigAcademia, atualizarConfigAcademia } from '../../../../lib/api'

const input = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2'
const ring = { '--tw-ring-color': 'var(--cor-destaque)' }
const btn = 'text-white px-5 py-2 rounded-lg text-sm font-medium transition disabled:opacity-60'
const btnStyle = { backgroundColor: 'var(--cor-destaque)' }

const DIAS = [
  ['seg', 'Segunda'], ['ter', 'Terça'], ['qua', 'Quarta'], ['qui', 'Quinta'],
  ['sex', 'Sexta'], ['sab', 'Sábado'], ['dom', 'Domingo'],
]

function horarioPadrao() {
  return { abre: '06:00', fecha: '22:00', fechado: false }
}

export default function AcademiaPage() {
  const { token } = useAuth()
  const [loading, setLoading] = useState(true)
  const [salvando, setSalvando] = useState(false)
  const [msg, setMsg] = useState({ tipo: '', texto: '' })

  const [dados, setDados] = useState({ nome: '', cnpj: '', telefone: '', email: '', endereco: '' })
  const [horarios, setHorarios] = useState(() =>
    Object.fromEntries(DIAS.map(([k]) => [k, horarioPadrao()]))
  )

  useEffect(() => {
    if (!token) return
    async function init() {
      try {
        const c = await getConfigAcademia(token)
        setDados({
          nome: c.nome || '', cnpj: c.cnpj || '', telefone: c.telefone || '',
          email: c.email || '', endereco: c.endereco || '',
        })
        setHorarios(prev => {
          const merged = { ...prev }
          for (const [k] of DIAS) {
            if (c.horarios && c.horarios[k]) merged[k] = { ...horarioPadrao(), ...c.horarios[k] }
          }
          return merged
        })
      } catch (err) {
        setMsg({ tipo: 'erro', texto: err.message })
      }
      setLoading(false)
    }
    init()
  }, [token])

  function setDia(dia, campo, valor) {
    setHorarios(h => ({ ...h, [dia]: { ...h[dia], [campo]: valor } }))
  }

  async function salvar(e) {
    e.preventDefault()
    setSalvando(true)
    setMsg({ tipo: '', texto: '' })
    try {
      await atualizarConfigAcademia(token, { ...dados, horarios })
      setMsg({ tipo: 'ok', texto: 'Configurações da academia salvas.' })
    } catch (err) {
      setMsg({ tipo: 'erro', texto: err.message })
    }
    setSalvando(false)
  }

  if (loading) return <p className="text-gray-400">Carregando...</p>

  return (
    <div className="max-w-3xl">
      <Link href="/admin/configuracoes" className="text-sm text-gray-500 hover:text-gray-700">
        ‹ Voltar para Configurações
      </Link>
      <h1 className="text-2xl font-bold text-gray-800 mt-2 mb-6">Academia</h1>

      <form onSubmit={salvar}>
        {/* Dados cadastrais */}
        <div className="bg-white rounded-xl shadow-sm p-5 mb-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Dados cadastrais</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="sm:col-span-2">
              <label className="text-xs text-gray-500 mb-1 block">Nome da academia</label>
              <input className={input} style={ring} placeholder="Ex: Academia Fitness Pro" value={dados.nome}
                onChange={e => setDados(d => ({ ...d, nome: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">CNPJ</label>
              <input className={input} style={ring} value={dados.cnpj} placeholder="00.000.000/0000-00"
                onChange={e => setDados(d => ({ ...d, cnpj: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">Telefone</label>
              <input className={input} style={ring} value={dados.telefone} placeholder="(11) 3333-4444"
                onChange={e => setDados(d => ({ ...d, telefone: e.target.value }))} />
            </div>
            <div>
              <label className="text-xs text-gray-500 mb-1 block">E-mail de contato</label>
              <input type="email" className={input} style={ring} placeholder="contato@academia.com" value={dados.email}
                onChange={e => setDados(d => ({ ...d, email: e.target.value }))} />
            </div>
            <div className="sm:col-span-2">
              <label className="text-xs text-gray-500 mb-1 block">Endereço</label>
              <input className={input} style={ring} placeholder="Rua, número, bairro, cidade, CEP" value={dados.endereco}
                onChange={e => setDados(d => ({ ...d, endereco: e.target.value }))} />
            </div>
          </div>
        </div>

        {/* Horários */}
        <div className="bg-white rounded-xl shadow-sm p-5 mb-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Horários de funcionamento</h2>
          <div className="space-y-2">
            {DIAS.map(([k, label]) => {
              const dia = horarios[k]
              return (
                <div key={k} className="flex items-center gap-3 flex-wrap">
                  <span className="w-20 text-sm text-gray-600">{label}</span>
                  <label className="flex items-center gap-1.5 text-xs text-gray-500 select-none">
                    <input type="checkbox" checked={dia.fechado}
                      onChange={e => setDia(k, 'fechado', e.target.checked)} />
                    Fechado
                  </label>
                  {!dia.fechado && (
                    <div className="flex items-center gap-2">
                      <input type="time" className="border border-gray-200 rounded-lg px-2 py-1 text-sm"
                        value={dia.abre || ''} onChange={e => setDia(k, 'abre', e.target.value)} />
                      <span className="text-gray-400 text-sm">às</span>
                      <input type="time" className="border border-gray-200 rounded-lg px-2 py-1 text-sm"
                        value={dia.fecha || ''} onChange={e => setDia(k, 'fecha', e.target.value)} />
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button type="submit" className={btn} style={btnStyle} disabled={salvando}>
            {salvando ? 'Salvando...' : 'Salvar alterações'}
          </button>
          {msg.texto && (
            <p className={`text-sm rounded-lg px-3 py-2 ${msg.tipo === 'erro' ? 'text-red-600 bg-red-50' : 'text-green-700 bg-green-50'}`}>
              {msg.texto}
            </p>
          )}
        </div>
      </form>
    </div>
  )
}
