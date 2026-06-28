/**
 * Testes unitários do hook useAuth.
 *
 * Estratégia:
 *   - Mocka `lib/supabase` para controlar getSession() e onAuthStateChange().
 *   - Mocka `next/navigation` para capturar redirects sem navegação real.
 *   - Usa `renderHook` do @testing-library/react para isolar o hook.
 *   - Usa `waitFor` para aguardar atualizações de estado assíncronas.
 */
import { renderHook, waitFor, act } from '@testing-library/react'
import { useAuth } from './useAuth'

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockReplace = jest.fn()

// next/navigation: o hook usa useRouter() apenas para .replace().
jest.mock('next/navigation', () => ({
  useRouter: () => ({ replace: mockReplace }),
}))

const mockGetSession          = jest.fn()
const mockOnAuthStateChange   = jest.fn()
const mockUnsubscribe         = jest.fn()

// lib/supabase: isolamos completamente o SDK — nenhum request de rede real.
jest.mock('../lib/supabase', () => ({
  supabase: {
    auth: {
      getSession:          (...args) => mockGetSession(...args),
      onAuthStateChange:   (...args) => mockOnAuthStateChange(...args),
    },
  },
}))

// Retorno padrão de onAuthStateChange: subscription com unsubscribe rastreável.
const mockSubscriptionResult = {
  data: { subscription: { unsubscribe: mockUnsubscribe } },
}

// ── Setup / teardown ──────────────────────────────────────────────────────────

beforeEach(() => {
  // resetAllMocks: limpa chamadas E reseta implementações (mockReturnValue, etc.).
  // clearAllMocks só limparia chamadas — implementações de testes anteriores
  // vazariam para o próximo teste e causariam resultados imprevisíveis.
  jest.resetAllMocks()
  // Por padrão, onAuthStateChange retorna a subscription sem disparar callback.
  mockOnAuthStateChange.mockReturnValue(mockSubscriptionResult)
})

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Configura mockGetSession para retornar uma sessão com o token dado.
 * Passa `null` para simular ausência de sessão.
 */
function mockSession(accessToken) {
  const session = accessToken ? { access_token: accessToken } : null
  mockGetSession.mockResolvedValue({ data: { session } })
}

/**
 * Configura mockOnAuthStateChange para expor o callback e permitir
 * que os testes disparem eventos de auth manualmente.
 */
function mockAuthListener() {
  let fireEvent
  mockOnAuthStateChange.mockImplementation((cb) => {
    fireEvent = cb
    return mockSubscriptionResult
  })
  return { fireEvent: (event, session) => act(() => fireEvent(event, session)) }
}

// ── Testes ────────────────────────────────────────────────────────────────────

describe('useAuth', () => {

  // ── Estado inicial ──────────────────────────────────────────────────────────

  it('começa com loading=true e token=null antes da sessão resolver', () => {
    // getSession nunca resolve durante este teste — estado "pendente".
    mockGetSession.mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useAuth())

    expect(result.current.loading).toBe(true)
    expect(result.current.token).toBeNull()
  })

  // ── Sessão válida ───────────────────────────────────────────────────────────

  it('expõe o token e define loading=false quando há sessão válida', async () => {
    mockSession('jwt-token-valido')

    const { result } = renderHook(() => useAuth())

    await waitFor(() => expect(result.current.loading).toBe(false))

    expect(result.current.token).toBe('jwt-token-valido')
    expect(mockReplace).not.toHaveBeenCalled()
  })

  // ── Sem sessão → redirect ───────────────────────────────────────────────────

  it('redireciona para /login quando não há sessão ativa', async () => {
    mockSession(null)

    const { result } = renderHook(() => useAuth())

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/login'))

    // Token permanece null; loading não chega a false (redirect acontece antes).
    expect(result.current.token).toBeNull()
  })

  // ── Evento SIGNED_OUT ───────────────────────────────────────────────────────

  it('redireciona e zera o token ao receber SIGNED_OUT', async () => {
    mockSession('token-pre-logout')
    const { fireEvent } = mockAuthListener()

    const { result } = renderHook(() => useAuth())
    await waitFor(() => expect(result.current.token).toBe('token-pre-logout'))

    // Simula o usuário fazendo logout em outra aba.
    fireEvent('SIGNED_OUT', null)

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/login'))
    expect(result.current.token).toBeNull()
  })

  it('redireciona quando o evento retorna session=null (qualquer evento)', async () => {
    mockSession('token-inicial')
    const { fireEvent } = mockAuthListener()

    renderHook(() => useAuth())
    await waitFor(() => expect(mockReplace).not.toHaveBeenCalled())

    // Evento desconhecido com session nula deve provocar redirect.
    fireEvent('USER_DELETED', null)

    await waitFor(() => expect(mockReplace).toHaveBeenCalledWith('/login'))
  })

  // ── TOKEN_REFRESHED ─────────────────────────────────────────────────────────

  it('atualiza o token sem redirecionar ao receber TOKEN_REFRESHED', async () => {
    mockSession('token-original')
    const { fireEvent } = mockAuthListener()

    const { result } = renderHook(() => useAuth())
    await waitFor(() => expect(result.current.token).toBe('token-original'))

    // SDK renovando o access_token silenciosamente (expirou mas refresh válido).
    fireEvent('TOKEN_REFRESHED', { access_token: 'token-renovado' })

    await waitFor(() => expect(result.current.token).toBe('token-renovado'))
    expect(mockReplace).not.toHaveBeenCalled()
  })

  // ── Evento INITIAL_SESSION ignorado ────────────────────────────────────────

  it('ignora INITIAL_SESSION para evitar setState duplicado', async () => {
    mockSession('meu-token')
    const { fireEvent } = mockAuthListener()

    const { result } = renderHook(() => useAuth())
    await waitFor(() => expect(result.current.token).toBe('meu-token'))

    // INITIAL_SESSION não deve alterar o estado nem provocar redirect.
    fireEvent('INITIAL_SESSION', { access_token: 'outro-token' })

    // Token permanece o original — INITIAL_SESSION foi ignorado.
    expect(result.current.token).toBe('meu-token')
    expect(mockReplace).not.toHaveBeenCalled()
  })

  // ── Cleanup / sem memory leak ───────────────────────────────────────────────

  it('chama unsubscribe ao desmontar o componente', async () => {
    mockSession('token-abc')

    const { unmount } = renderHook(() => useAuth())
    await waitFor(() => expect(mockUnsubscribe).not.toHaveBeenCalled())

    unmount()

    expect(mockUnsubscribe).toHaveBeenCalledTimes(1)
  })

  it('não atualiza estado após desmontar (evita memory leak)', async () => {
    // getSession resolve somente depois do unmount.
    let resolveSession
    mockGetSession.mockReturnValue(
      new Promise((res) => { resolveSession = res })
    )

    const { result, unmount } = renderHook(() => useAuth())
    unmount()

    // Resolve a Promise depois do unmount — a flag `active` bloqueia o setState.
    // O React NÃO deve emitir warning de "Can't perform a React state update
    // on an unmounted component".
    // await act(async) é necessário para que o React 19 consiga draining
    // microtasks pendentes sem deixar o scheduler em estado sujo entre testes.
    await act(async () => {
      resolveSession({ data: { session: { access_token: 'token-tardio' } } })
    })

    // Token continua null: o setState foi suprimido pelo flag `active`.
    expect(result.current.token).toBeNull()
  })

  it('não redireciona quando onAuthStateChange dispara depois do unmount', async () => {
    mockSession('token-normal')
    const { fireEvent } = mockAuthListener()

    const { unmount } = renderHook(() => useAuth())
    await waitFor(() => expect(mockReplace).not.toHaveBeenCalled())

    unmount()

    // Após unmount, SIGNED_OUT não deve causar redirect.
    // await fireEvent (que já encapsula act) evita act não-awaited vazar entre testes.
    await fireEvent('SIGNED_OUT', null)

    expect(mockReplace).not.toHaveBeenCalled()
  })

  // ── onAuthStateChange registrado na montagem ────────────────────────────────

  it('registra o listener de auth ao montar e unsubscribe ao desmontar', async () => {
    mockSession('qualquer-token')
    const { fireEvent } = mockAuthListener()

    const { result, unmount } = renderHook(() => useAuth())

    // Aguarda token — confirma que o efeito rodou (e portanto o listener foi registrado).
    await waitFor(() => expect(result.current.token).toBe('qualquer-token'))

    // Listener registrado: conseguimos disparar eventos e o hook reage a eles.
    // toHaveBeenCalled() em vez de CalledTimes(1): React 19 StrictMode executa
    // useEffect duas vezes (mount→cleanup→mount) — o que importa é que foi chamado.
    expect(mockOnAuthStateChange).toHaveBeenCalled()

    // Listener removido no cleanup (StrictMode também gera uma chamada extra).
    unmount()
    expect(mockUnsubscribe).toHaveBeenCalled()

    // Após unmount, SIGNED_OUT não deve causar nenhum efeito.
    fireEvent('SIGNED_OUT', null)
    expect(mockReplace).not.toHaveBeenCalled()
  })
})
