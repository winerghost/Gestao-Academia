import { render, screen } from '@testing-library/react'
import Toast from './Toast'

describe('Toast', () => {
  it('não renderiza nada quando message vazio', () => {
    const { container } = render(<Toast message="" type="success" />)
    expect(container.firstChild).toBeNull()
  })

  it('não renderiza nada quando message falsy', () => {
    const { container } = render(<Toast message={null} type="success" />)
    expect(container.firstChild).toBeNull()
  })

  it('renderiza mensagem quando message fornecida', () => {
    render(<Toast message="Sucesso!" type="success" />)
    expect(screen.getByText('Sucesso!')).toBeInTheDocument()
  })

  it('usa tipo default "success"', () => {
    render(<Toast message="Test" />)
    expect(screen.getByText('Test')).toBeInTheDocument()
  })

  it('renderiza ícone "✓" para type="success"', () => {
    render(<Toast message="OK" type="success" />)
    expect(screen.getByText('✓')).toBeInTheDocument()
  })

  it('renderiza ícone "⚠" para type="error"', () => {
    render(<Toast message="Erro" type="error" />)
    expect(screen.getByText('⚠')).toBeInTheDocument()
  })

  it('aplica cores corretas para success', () => {
    const { container } = render(<Toast message="OK" type="success" />)
    const toast = container.firstChild
    expect(toast).toHaveClass('bg-green-50', 'border-green-200')
  })

  it('aplica cores corretas para error', () => {
    const { container } = render(<Toast message="Erro" type="error" />)
    const toast = container.firstChild
    expect(toast).toHaveClass('bg-red-50', 'border-red-200')
  })

  it('posiciona fixo no topo à direita', () => {
    const { container } = render(<Toast message="Test" />)
    const toast = container.firstChild
    expect(toast).toHaveClass('fixed', 'top-4', 'right-4')
  })

  it('tem animação slideIn', () => {
    const { container } = render(<Toast message="Test" />)
    const toast = container.firstChild
    expect(toast).toHaveClass('animate-slideIn')
  })
})
