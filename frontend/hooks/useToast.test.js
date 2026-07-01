import { renderHook, act } from '@testing-library/react'
import { useToast } from './useToast'

describe('useToast', () => {
  beforeEach(() => {
    jest.useFakeTimers()
  })

  afterEach(() => {
    jest.runOnlyPendingTimers()
    jest.useRealTimers()
  })

  it('inicializa com toast = null', () => {
    const { result } = renderHook(() => useToast())
    expect(result.current.toast).toBeNull()
  })

  it('show() seta o toast com mensagem e tipo', () => {
    const { result } = renderHook(() => useToast())

    act(() => {
      result.current.show('Sucesso!', 'success')
    })

    expect(result.current.toast).toEqual({ message: 'Sucesso!', type: 'success' })
  })

  it('show() usa tipo default "success"', () => {
    const { result } = renderHook(() => useToast())

    act(() => {
      result.current.show('Mensagem')
    })

    expect(result.current.toast.type).toBe('success')
  })

  it('dismiss() limpa o toast', () => {
    const { result } = renderHook(() => useToast())

    act(() => {
      result.current.show('Teste')
    })

    expect(result.current.toast).not.toBeNull()

    act(() => {
      result.current.dismiss()
    })

    expect(result.current.toast).toBeNull()
  })

  it('timeout de 3.5s limpa automaticamente', () => {
    const { result } = renderHook(() => useToast())

    act(() => {
      result.current.show('Desaparece sozinho')
    })

    expect(result.current.toast).not.toBeNull()

    act(() => {
      jest.advanceTimersByTime(3500)
    })

    expect(result.current.toast).toBeNull()
  })

  it('antes de 3.5s o toast ainda está visível', () => {
    const { result } = renderHook(() => useToast())

    act(() => {
      result.current.show('Visível')
    })

    act(() => {
      jest.advanceTimersByTime(3000)
    })

    expect(result.current.toast).not.toBeNull()
  })
})
