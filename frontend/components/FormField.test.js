import { render, screen } from '@testing-library/react'
import FormField, { inputClass } from './FormField'

describe('FormField', () => {
  it('renderiza label quando fornecido', () => {
    render(
      <FormField label="E-mail">
        <input type="text" />
      </FormField>
    )
    expect(screen.getByText('E-mail')).toBeInTheDocument()
  })

  it('não renderiza label quando não fornecido', () => {
    render(
      <FormField>
        <input type="text" />
      </FormField>
    )
    expect(screen.queryByText(/./)).toBeNull()
  })

  it('mostra asterisco quando required=true', () => {
    render(
      <FormField label="Obrigatório" required>
        <input type="text" />
      </FormField>
    )
    expect(screen.getByText('*')).toBeInTheDocument()
  })

  it('não mostra asterisco quando required=false', () => {
    render(
      <FormField label="Opcional" required={false}>
        <input type="text" />
      </FormField>
    )
    expect(screen.queryByText('*')).not.toBeInTheDocument()
  })

  it('mostra mensagem de erro quando error fornecido', () => {
    render(
      <FormField label="Campo" error="Algo deu errado">
        <input type="text" />
      </FormField>
    )
    expect(screen.getByText('Algo deu errado')).toBeInTheDocument()
  })

  it('mostra hint quando não há error', () => {
    render(
      <FormField label="Campo" hint="Dica útil">
        <input type="text" />
      </FormField>
    )
    expect(screen.getByText('Dica útil')).toBeInTheDocument()
  })

  it('não mostra hint quando há error', () => {
    render(
      <FormField label="Campo" error="Erro" hint="Dica">
        <input type="text" />
      </FormField>
    )
    expect(screen.queryByText('Dica')).not.toBeInTheDocument()
    expect(screen.getByText('Erro')).toBeInTheDocument()
  })

  it('renderiza children', () => {
    render(
      <FormField label="Campo">
        <input type="email" data-testid="email-input" />
      </FormField>
    )
    expect(screen.getByTestId('email-input')).toBeInTheDocument()
  })

  it('aplica className customizado', () => {
    const { container } = render(
      <FormField label="Campo" className="col-span-2">
        <input type="text" />
      </FormField>
    )
    expect(container.firstChild).toHaveClass('col-span-2')
  })
})

describe('inputClass', () => {
  it('retorna classe com borda vermelha quando hasError=true', () => {
    const cls = inputClass(true)
    expect(cls).toContain('border-red-300')
    expect(cls).toContain('ring-red-200')
    expect(cls).toContain('focus:ring-red-400')
  })

  it('retorna classe com borda cinza quando hasError=false', () => {
    const cls = inputClass(false)
    expect(cls).toContain('border-gray-200')
    expect(cls).toContain('focus:ring-orange-500')
    expect(cls).not.toContain('border-red-300')
  })

  it('sempre inclui classes base', () => {
    const cls = inputClass(true)
    expect(cls).toContain('w-full')
    expect(cls).toContain('border')
    expect(cls).toContain('rounded-lg')
  })
})
