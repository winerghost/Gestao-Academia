import { mascaraTelefone } from './masks'

describe('mascaraTelefone', () => {
  it('retorna string vazia se valor vazio', () => {
    expect(mascaraTelefone('')).toBe('')
    expect(mascaraTelefone(null)).toBe('')
  })

  it('formata 1-2 dígitos sem separador', () => {
    expect(mascaraTelefone('1')).toBe('1')
    expect(mascaraTelefone('11')).toBe('11')
  })

  it('formata 3-6 dígitos como (XX) X...', () => {
    expect(mascaraTelefone('119')).toBe('(11) 9')
    expect(mascaraTelefone('1199')).toBe('(11) 99')
    expect(mascaraTelefone('11999')).toBe('(11) 999')
    expect(mascaraTelefone('119999')).toBe('(11) 9999')
  })

  it('formata 7-10 dígitos com hífen a partir de 7', () => {
    expect(mascaraTelefone('1199999')).toBe('(11) 99999-')
    expect(mascaraTelefone('11999999')).toBe('(11) 99999-9')
    expect(mascaraTelefone('119999999')).toBe('(11) 99999-99')
    expect(mascaraTelefone('1199999999')).toBe('(11) 99999-999')
  })

  it('formata 11 dígitos com limite em 9999', () => {
    expect(mascaraTelefone('11999999999')).toBe('(11) 99999-9999')
  })

  it('limita a 11 dígitos (excesso ignorado)', () => {
    expect(mascaraTelefone('119999999999')).toBe('(11) 99999-9999')
    expect(mascaraTelefone('11999999999999')).toBe('(11) 99999-9999')
  })

  it('remove caracteres não numéricos', () => {
    expect(mascaraTelefone('(11) 99999-9999')).toBe('(11) 99999-9999')
    expect(mascaraTelefone('11 9 9999-9999')).toBe('(11) 99999-9999')
    // 11#9999$99999 = 1199999999 (10 dígitos)
    expect(mascaraTelefone('11#9999$99999')).toBe('(11) 99999-9999')
  })

  it('formata input com caracteres especiais misturados', () => {
    expect(mascaraTelefone('(11)99999-9999')).toBe('(11) 99999-9999')
    expect(mascaraTelefone('11.99999.9999')).toBe('(11) 99999-9999')
  })
})
