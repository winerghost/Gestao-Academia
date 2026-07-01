import { render, screen, fireEvent } from '@testing-library/react'
import ModalConfirmacao from './ModalConfirmacao'

describe('ModalConfirmacao', () => {
  const mockCallbacks = {
    aoConfirmar: jest.fn(),
    aoCancelar: jest.fn(),
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('não renderiza quando aberto=false', () => {
    const { container } = render(
      <ModalConfirmacao
        aberto={false}
        titulo="Teste"
        {...mockCallbacks}
      />
    )
    const dialog = container.querySelector('dialog')
    expect(dialog).not.toHaveAttribute('open')
  })

  it('renderiza quando aberto=true', () => {
    const { container } = render(
      <ModalConfirmacao
        aberto={true}
        titulo="Teste"
        {...mockCallbacks}
      />
    )
    const dialog = container.querySelector('dialog')
    expect(dialog).toBeInTheDocument()
  })

  it('exibe o título', () => {
    render(
      <ModalConfirmacao
        aberto={true}
        titulo="Confirmar exclusão"
        {...mockCallbacks}
      />
    )
    expect(screen.getByText('Confirmar exclusão')).toBeInTheDocument()
  })

  it('exibe a mensagem', () => {
    render(
      <ModalConfirmacao
        aberto={true}
        mensagem="Tem certeza?"
        {...mockCallbacks}
      />
    )
    expect(screen.getByText('Tem certeza?')).toBeInTheDocument()
  })

  it('mostra ícone ⚠ quando perigoso=true', () => {
    render(
      <ModalConfirmacao
        aberto={true}
        perigoso={true}
        {...mockCallbacks}
      />
    )
    expect(screen.getByText('⚠')).toBeInTheDocument()
  })

  it('mostra ícone ℹ quando perigoso=false', () => {
    render(
      <ModalConfirmacao
        aberto={true}
        perigoso={false}
        {...mockCallbacks}
      />
    )
    expect(screen.getByText('ℹ')).toBeInTheDocument()
  })

  it('chama aoConfirmar ao clicar em Confirmar', () => {
    render(
      <ModalConfirmacao
        aberto={true}
        botaoConfirmar="Excluir"
        {...mockCallbacks}
      />
    )
    const btn = screen.getByText('Excluir')
    fireEvent.click(btn)
    expect(mockCallbacks.aoConfirmar).toHaveBeenCalledTimes(1)
  })

  it('chama aoCancelar ao clicar em Cancelar', () => {
    render(
      <ModalConfirmacao
        aberto={true}
        botaoCancelar="Cancelar"
        {...mockCallbacks}
      />
    )
    const btn = screen.getByText('Cancelar')
    fireEvent.click(btn)
    expect(mockCallbacks.aoCancelar).toHaveBeenCalledTimes(1)
  })

  it('desabilita botões quando carregando=true', () => {
    const { container } = render(
      <ModalConfirmacao
        aberto={true}
        botaoConfirmar="Confirmar"
        botaoCancelar="Cancelar"
        carregando={true}
        {...mockCallbacks}
      />
    )
    const buttons = container.querySelectorAll('button')
    buttons.forEach((btn) => {
      expect(btn).toBeDisabled()
    })
  })

  it('mostra "..." no botão de ação quando carregando=true', () => {
    render(
      <ModalConfirmacao
        aberto={true}
        botaoConfirmar="Confirmar"
        carregando={true}
        {...mockCallbacks}
      />
    )
    expect(screen.getByText('...')).toBeInTheDocument()
  })

  it('usa labels customizados dos botões', () => {
    render(
      <ModalConfirmacao
        aberto={true}
        botaoConfirmar="Sim, excluir"
        botaoCancelar="Não, cancelar"
        {...mockCallbacks}
      />
    )
    expect(screen.getByText('Sim, excluir')).toBeInTheDocument()
    expect(screen.getByText('Não, cancelar')).toBeInTheDocument()
  })

  it('apply cores vermelhas quando perigoso=true', () => {
    const { container } = render(
      <ModalConfirmacao
        aberto={true}
        perigoso={true}
        botaoConfirmar="Excluir"
        {...mockCallbacks}
      />
    )
    const btnConfirmar = screen.getByText('Excluir')
    expect(btnConfirmar).toHaveClass('bg-red-600')
  })

  it('apply cores laranja quando perigoso=false', () => {
    const { container } = render(
      <ModalConfirmacao
        aberto={true}
        perigoso={false}
        botaoConfirmar="Confirmar"
        {...mockCallbacks}
      />
    )
    const btnConfirmar = screen.getByText('Confirmar')
    expect(btnConfirmar).toHaveClass('bg-orange-500')
  })
})
