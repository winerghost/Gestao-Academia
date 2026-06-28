'use client'
import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { useAuth } from '../../../../hooks/useAuth'
import { getAluno, atualizarAluno, vincularPlanoAluno, getMensalidades, getPlanos, pagarMensalidade, getAvaliacoes, adminUploadAvatarUsuario, adminRemoverAvatarUsuario } from '../../../../lib/api'
import { AlunoDetalheSkeleton } from './_skeleton'
import CapturaFoto from '../_CapturaFoto'

const BADGE = {
  ativo: 'bg-green-100 text-green-700',
  inativo: 'bg-gray-100 text-gray-500',
  inadimplente: 'bg-red-100 text-red-700',
  paga: 'bg-green-100 text-green-700',
  pendente: 'bg-yellow-100 text-yellow-700',
  atrasada: 'bg-red-100 text-red-700',
}

function Info({ label, value }) {
  return (
    <div className="flex justify-between py-1.5 border-b border-gray-50 last:border-0">
      <dt className="text-sm text-gray-500">{label}</dt>
      <dd className="text-sm text-gray-800 font-medium text-right max-w-[60%]">{value || '—'}</dd>
    </div>
  )
}

export default function AlunoDetalhe() {
  const { token } = useAuth()
  const { id } = useParams()
  const [aluno, setAluno] = useState(null)
  const [mensalidades, setMensalidades] = useState([])
  const [planos, setPlanos] = useState([])
  const [avaliacoes, setAvaliacoes] = useState([])
  const [loading, setLoading] = useState(true)
  const [editando, setEditando] = useState(false)
  const [form, setForm] = useState({})
  const [novoPlano, setNovoPlano] = useState({ plano_id: '', data_inicio: '' })
  const [erro, setErro] = useState('')
  const [salvando, setSalvando] = useState(false)
  const [fotoMsg, setFotoMsg] = useState('')
  const [fotoBusy, setFotoBusy] = useState(false)

  async function carregar(t) {
    const [a, m, p, av] = await Promise.all([
      getAluno(t, id),
      getMensalidades(t, { aluno_id: id }),
      getPlanos(t),
      getAvaliacoes(t, { aluno_id: id }),
    ])
    setAluno(a)
    setForm({
      cpf: a.cpf || '',
      telefone: a.profiles?.telefone || '',
      data_nascimento: a.data_nascimento || '',
      endereco: a.endereco || '',
      frequencia_habilitada: a.frequencia_habilitada || false,
    })
    setMensalidades(m)
    setPlanos(p)
    setAvaliacoes(av)
  }

  useEffect(() => {
    if (!token) return
    async function init() {
      await carregar(token)
      setLoading(false)
    }
    init()
  }, [token, id])

  async function salvarEdicao() {
    setSalvando(true)
    setErro('')
    try {
      await atualizarAluno(token, id, form)
      await carregar(token)
      setEditando(false)
    } catch (err) {
      setErro(err.message)
    }
    setSalvando(false)
  }

  async function vincularPlano() {
    if (!novoPlano.plano_id || !novoPlano.data_inicio) {
      setErro('Selecione plano e data de início.')
      return
    }
    setSalvando(true)
    setErro('')
    try {
      await vincularPlanoAluno(token, id, novoPlano)
      setNovoPlano({ plano_id: '', data_inicio: '' })
      await carregar(token)
    } catch (err) {
      setErro(err.message)
    }
    setSalvando(false)
  }

  // Troca/remoção de foto do aluno (admin/recepcionista). O CapturaFoto entrega
  // um data URL (webcam/arquivo) ou null (remover); convertemos para File no upload.
  async function mudarFotoAluno(dataUrl) {
    setFotoMsg('')
    setFotoBusy(true)
    try {
      if (dataUrl) {
        const blob = await (await fetch(dataUrl)).blob()
        const file = new File([blob], 'foto.jpg', { type: blob.type || 'image/jpeg' })
        await adminUploadAvatarUsuario(token, aluno.profile_id, file)
        setFotoMsg('Foto atualizada.')
      } else {
        await adminRemoverAvatarUsuario(token, aluno.profile_id)
        setFotoMsg('Foto removida.')
      }
      await carregar(token)
    } catch (err) {
      setFotoMsg(err.message)
    }
    setFotoBusy(false)
  }

  async function pagar(mensalidadeId) {
    if (!confirm('Confirmar pagamento desta mensalidade?')) return
    try {
      await pagarMensalidade(token, mensalidadeId)
      await carregar(token)
    } catch (err) {
      alert(err.message)
    }
  }

  const input = "w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500 bg-white"

  if (loading) return <AlunoDetalheSkeleton />
  if (!aluno) return <p className="text-red-500">Aluno não encontrado.</p>

  const profile = aluno.profiles || {}
  const totalPago = mensalidades.filter(m => m.status === 'paga').reduce((s, m) => s + (m.valor_total || 0), 0)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 flex-wrap">
          <Link href="/admin/alunos" className="text-sm text-gray-500 hover:text-gray-700">← Alunos</Link>
          <span className="text-gray-300">/</span>
          <h1 className="text-2xl font-bold text-gray-800">{profile.nome}</h1>
          <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full capitalize ${BADGE[aluno.status]}`}>
            {aluno.status}
          </span>
        </div>
        {!editando && (
          <button onClick={() => setEditando(true)}
            className="border border-gray-200 bg-white hover:bg-gray-50 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium transition">
            ✏️ Editar
          </button>
        )}
      </div>

      {/* Foto do aluno */}
      <div className="bg-white rounded-xl shadow-sm p-5">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Foto do aluno</h2>
        <CapturaFoto
          value={profile.avatar_url}
          nome={profile.nome}
          onChange={mudarFotoAluno}
          disabled={fotoBusy}
        />
        {fotoMsg && <p className="text-xs text-gray-500 mt-2">{fotoMsg}</p>}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Dados / edição */}
        <div className="bg-white rounded-xl shadow-sm p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Dados pessoais</h2>
          {editando ? (
            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-500">CPF</label>
                <input className={input} placeholder="000.000.000-00" value={form.cpf} onChange={e => setForm(f => ({ ...f, cpf: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs text-gray-500">Telefone</label>
                <input className={input} value={form.telefone} onChange={e => setForm(f => ({ ...f, telefone: e.target.value }))} placeholder="(11) 99999-9999" />
              </div>
              <div>
                <label className="text-xs text-gray-500">Data de nascimento</label>
                <input type="date" className={input} value={form.data_nascimento} onChange={e => setForm(f => ({ ...f, data_nascimento: e.target.value }))} />
              </div>
              <div>
                <label className="text-xs text-gray-500">Endereço</label>
                <input className={input} placeholder="Rua, número, bairro, cidade" value={form.endereco} onChange={e => setForm(f => ({ ...f, endereco: e.target.value }))} />
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" id="freqEdit" checked={form.frequencia_habilitada}
                  onChange={e => setForm(f => ({ ...f, frequencia_habilitada: e.target.checked }))}
                  className="accent-orange-500" />
                <label htmlFor="freqEdit" className="text-xs text-gray-600">Frequência habilitada</label>
              </div>
              {erro && <p className="text-xs text-red-500">{erro}</p>}
              <div className="flex gap-2 pt-1">
                <button onClick={salvarEdicao} disabled={salvando}
                  className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-1.5 rounded-lg text-xs font-medium transition disabled:opacity-60">
                  {salvando ? 'Salvando...' : 'Salvar'}
                </button>
                <button onClick={() => setEditando(false)}
                  className="border border-gray-200 text-gray-600 px-4 py-1.5 rounded-lg text-xs font-medium hover:bg-gray-50 transition">
                  Cancelar
                </button>
              </div>
            </div>
          ) : (
            <dl>
              <Info label="CPF" value={aluno.cpf} />
              <Info label="Telefone" value={profile.telefone} />
              <Info label="Nascimento" value={aluno.data_nascimento} />
              <Info label="Endereço" value={aluno.endereco} />
              <Info label="Frequência" value={aluno.frequencia_habilitada ? '✅ Habilitada' : 'Não habilitada'} />
              <Info label="Cadastro" value={aluno.created_at?.slice(0, 10)} />
            </dl>
          )}
        </div>

        {/* Planos */}
        <div className="bg-white rounded-xl shadow-sm p-5 space-y-4">
          <h2 className="text-sm font-semibold text-gray-700">Planos vinculados</h2>
          {!(aluno.aluno_planos?.length) ? (
            <p className="text-xs text-gray-400">Nenhum plano vinculado.</p>
          ) : (
            <div className="space-y-2">
              {aluno.aluno_planos.map(ap => (
                <div key={ap.id} className="flex justify-between items-center py-1">
                  <div>
                    <p className="text-sm font-medium text-gray-700">{ap.planos?.nome}</p>
                    <p className="text-xs text-gray-400">Início: {ap.data_inicio}</p>
                  </div>
                  <span className={`text-xs px-2 py-0.5 rounded-full capitalize ${BADGE[ap.status] || 'bg-gray-100 text-gray-500'}`}>
                    {ap.status}
                  </span>
                </div>
              ))}
            </div>
          )}
          <div className="border-t pt-3 space-y-2">
            <p className="text-xs font-semibold text-gray-500">Vincular novo plano</p>
            <select className={input} value={novoPlano.plano_id} onChange={e => setNovoPlano(p => ({ ...p, plano_id: e.target.value }))}>
              <option value="">Selecione um plano...</option>
              {planos.filter(p => p.ativo !== false).map(p => (
                <option key={p.id} value={p.id}>{p.nome} — R$ {Number(p.valor).toFixed(2)}</option>
              ))}
            </select>
            <input type="date" className={input} value={novoPlano.data_inicio}
              onChange={e => setNovoPlano(p => ({ ...p, data_inicio: e.target.value }))} />
            {erro && !editando && <p className="text-xs text-red-500">{erro}</p>}
            <button onClick={vincularPlano} disabled={salvando}
              className="w-full bg-orange-500 hover:bg-orange-600 text-white py-2 rounded-lg text-xs font-medium transition disabled:opacity-60">
              {salvando ? 'Vinculando...' : 'Vincular plano'}
            </button>
          </div>
        </div>

        {/* Resumo financeiro */}
        <div className="bg-white rounded-xl shadow-sm p-5">
          <h2 className="text-sm font-semibold text-gray-700 mb-3">Resumo financeiro</h2>
          <dl>
            <Info label="Mensalidades pagas" value={mensalidades.filter(m => m.status === 'paga').length} />
            <Info label="Pendentes" value={mensalidades.filter(m => m.status === 'pendente').length} />
            <Info label="Atrasadas" value={mensalidades.filter(m => m.status === 'atrasada').length} />
            <Info label="Total pago" value={`R$ ${totalPago.toFixed(2)}`} />
          </dl>
        </div>
      </div>

      {/* Avaliações físicas */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-700">Avaliações físicas</h2>
          <Link
            href={`/admin/avaliacoes/nova?aluno_id=${id}`}
            className="text-xs text-orange-500 hover:text-orange-700 font-medium transition"
          >
            ➕ Nova avaliação
          </Link>
        </div>
        {avaliacoes.length === 0 ? (
          <p className="text-center text-gray-400 py-6 text-sm">Nenhuma avaliação cadastrada.</p>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                {['Data', 'Peso', 'Altura', 'IMC', '% Gordura', 'Massa Magra', ''].map(h => (
                  <th key={h} className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {avaliacoes.map(av => (
                <tr key={av.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm text-gray-700">{av.data_avaliacao}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{av.peso_kg ? `${av.peso_kg} kg` : '—'}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{av.altura_cm ? `${av.altura_cm} cm` : '—'}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{av.imc ?? '—'}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{av.gordura_corporal ? `${av.gordura_corporal}%` : '—'}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{av.massa_magra_kg ? `${av.massa_magra_kg} kg` : '—'}</td>
                  <td className="px-4 py-3">
                    <Link href={`/admin/avaliacoes/${av.id}`} className="text-orange-500 hover:text-orange-700 text-xs font-medium">
                      Ver →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Mensalidades */}
      <div className="bg-white rounded-xl shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="text-sm font-semibold text-gray-700">Mensalidades</h2>
        </div>
        {mensalidades.length === 0 ? (
          <p className="text-center text-gray-400 py-8 text-sm">Nenhuma mensalidade encontrada.</p>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                {['Plano', 'Vencimento', 'Valor', 'Juros', 'Total', 'Status', 'Ações'].map(h => (
                  <th key={h} className="px-4 py-2.5 text-left text-xs font-semibold text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {mensalidades.map(m => (
                <tr key={m.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-sm text-gray-700">{m.aluno_planos?.planos?.nome || '—'}</td>
                  <td className="px-4 py-3 text-sm text-gray-500">{m.data_vencimento}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">R$ {Number(m.valor).toFixed(2)}</td>
                  <td className="px-4 py-3 text-sm text-red-500">{m.juros > 0 ? `R$ ${Number(m.juros).toFixed(2)}` : '—'}</td>
                  <td className="px-4 py-3 text-sm font-semibold text-gray-800">R$ {Number(m.valor_total).toFixed(2)}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs px-2.5 py-0.5 rounded-full font-medium capitalize ${BADGE[m.status]}`}>{m.status}</span>
                  </td>
                  <td className="px-4 py-3">
                    {m.status !== 'paga' ? (
                      <button onClick={() => pagar(m.id)}
                        className="text-orange-500 hover:text-orange-700 text-xs font-medium">
                        Registrar pagamento
                      </button>
                    ) : (
                      <span className="text-xs text-gray-400">Pago em {m.data_pagamento}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
