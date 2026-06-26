const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000'

async function fetcher(endpoint, token, options = {}) {
  const res = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.error || `Erro ${res.status}`)
  }
  return res.json()
}

export async function downloadRelatorio(token, endpoint) {
  const res = await fetch(`${API_URL}${endpoint}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  if (!res.ok) throw new Error('Erro ao gerar relatório')
  const blob = await res.blob()
  const cd = res.headers.get('Content-Disposition') || ''
  const match = cd.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/)
  const filename = match ? match[1].replace(/['"]/g, '') : 'relatorio'
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// Auth
export const getMe = (token) => fetcher('/auth/me', token)

// Portal do aluno
export const getPortalMe = (token) => fetcher('/portal/me', token)
export const getPortalMensalidades = (token) => fetcher('/portal/mensalidades', token)
export const getPortalFrequencias = (token) => fetcher('/portal/frequencias', token)

// Alunos
export const getAlunos = (token, params = {}) => {
  const qs = new URLSearchParams(params).toString()
  return fetcher(`/alunos${qs ? `?${qs}` : ''}`, token)
}
export const getAluno = (token, id) => fetcher(`/alunos/${id}`, token)
export const criarAluno = (token, data) =>
  fetcher('/alunos', token, { method: 'POST', body: JSON.stringify(data) })
export const atualizarAluno = (token, id, data) =>
  fetcher(`/alunos/${id}`, token, { method: 'PUT', body: JSON.stringify(data) })
export const vincularPlanoAluno = (token, alunoId, data) =>
  fetcher(`/alunos/${alunoId}/planos`, token, { method: 'POST', body: JSON.stringify(data) })

// Instrutores
export const getInstrutores = (token) => fetcher('/instrutores', token)
export const getInstrutor = (token, id) => fetcher(`/instrutores/${id}`, token)
export const criarInstrutor = (token, data) =>
  fetcher('/instrutores', token, { method: 'POST', body: JSON.stringify(data) })
export const atualizarInstrutor = (token, id, data) =>
  fetcher(`/instrutores/${id}`, token, { method: 'PUT', body: JSON.stringify(data) })
export const getInstrutorPlanos = (token, id) => fetcher(`/instrutores/${id}/planos`, token)
export const vincularPlanoInstrutor = (token, instrutorId, planoId) =>
  fetcher(`/instrutores/${instrutorId}/planos`, token, {
    method: 'POST', body: JSON.stringify({ plano_id: planoId }),
  })
export const desvincularPlanoInstrutor = (token, instrutorId, ipId) =>
  fetcher(`/instrutores/${instrutorId}/planos/${ipId}`, token, { method: 'DELETE' })

// Planos
export const getPlanos = (token) => fetcher('/planos', token)
export const criarPlano = (token, data) =>
  fetcher('/planos', token, { method: 'POST', body: JSON.stringify(data) })
export const atualizarPlano = (token, id, data) =>
  fetcher(`/planos/${id}`, token, { method: 'PUT', body: JSON.stringify(data) })
export const togglePlanoAtivo = (token, id) =>
  fetcher(`/planos/${id}/ativo`, token, { method: 'PATCH' })

// Mensalidades
export const getMensalidades = (token, params = {}) => {
  const qs = new URLSearchParams(params).toString()
  return fetcher(`/mensalidades${qs ? `?${qs}` : ''}`, token)
}
export const pagarMensalidade = (token, id) =>
  fetcher(`/mensalidades/${id}/pagar`, token, { method: 'POST' })

// Dashboard
export const getDashboardAlunos = (token) => fetcher('/dashboard/alunos', token)
export const getDashboardFinanceiro = (token) => fetcher('/dashboard/financeiro', token)
export const getDashboardFrequencia = (token) => fetcher('/dashboard/frequencia', token)

// Avaliações
export const getAvaliacoes = (token, params = {}) => {
  const qs = new URLSearchParams(params).toString()
  return fetcher(`/avaliacoes${qs ? `?${qs}` : ''}`, token)
}
export const getAvaliacao = (token, id) => fetcher(`/avaliacoes/${id}`, token)
export const criarAvaliacao = (token, data) =>
  fetcher('/avaliacoes', token, { method: 'POST', body: JSON.stringify(data) })
export const atualizarAvaliacao = (token, id, data) =>
  fetcher(`/avaliacoes/${id}`, token, { method: 'PUT', body: JSON.stringify(data) })
export const deletarAvaliacao = (token, id) =>
  fetcher(`/avaliacoes/${id}`, token, { method: 'DELETE' })
