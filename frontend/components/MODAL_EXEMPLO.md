# ModalConfirmacao — Componente de Diálogo Elegante

## Características

- ✅ Usa `<dialog>` HTML nativo (semântico e acessível)
- ✅ Backdrop click para fechar (clique fora do modal)
- ✅ Suporte a estados de carregamento
- ✅ Variações perigoso/normal com cores diferentes
- ✅ Styling moderno com Tailwind

## Uso Básico

```jsx
import ModalConfirmacao from '@/components/ModalConfirmacao'
import { useState } from 'react'

export default function MyComponent() {
  const [usuarioParaExcluir, setUsuarioParaExcluir] = useState(null)
  const [carregando, setCarregando] = useState(false)

  async function confirmar() {
    setCarregando(true)
    try {
      await excluirUsuario(usuarioParaExcluir.id)
      setUsuarioParaExcluir(null)
    } finally {
      setCarregando(false)
    }
  }

  return (
    <>
      <button onClick={() => setUsuarioParaExcluir({ id: 1, nome: 'João' })}>
        Excluir
      </button>

      <ModalConfirmacao
        aberto={!!usuarioParaExcluir}
        titulo="Excluir usuário"
        mensagem={usuarioParaExcluir ? `Tem certeza que deseja excluir ${usuarioParaExcluir.nome}?` : ''}
        botaoConfirmar="Excluir"
        botaoCancelar="Cancelar"
        perigoso={true}
        aoConfirmar={confirmar}
        aoCancelar={() => setUsuarioParaExcluir(null)}
        carregando={carregando}
      />
    </>
  )
}
```

## Props

| Prop | Tipo | Padrão | Descrição |
|------|------|--------|-----------|
| `aberto` | boolean | `false` | Controla se o modal está visível |
| `titulo` | string | `"Confirmar ação"` | Título do modal |
| `mensagem` | string | `"Tem certeza que deseja continuar?"` | Corpo da mensagem |
| `botaoConfirmar` | string | `"Confirmar"` | Label do botão de confirmação |
| `botaoCancelar` | string | `"Cancelar"` | Label do botão de cancelamento |
| `perigoso` | boolean | `false` | Se `true`, usa cores vermelhas (aviso) |
| `aoConfirmar` | function | `() => {}` | Callback quando usuário clica em confirmar |
| `aoCancelar` | function | `() => {}` | Callback quando usuário clica em cancelar |
| `carregando` | boolean | `false` | Se `true`, desabilita botões e mostra `...` |

## Variações

### Modal Normal (info)
```jsx
<ModalConfirmacao
  aberto={true}
  titulo="Enviar?"
  mensagem="Deseja realmente enviar esta mensagem?"
  perigoso={false}
/>
```

### Modal Perigoso (exclusão)
```jsx
<ModalConfirmacao
  aberto={true}
  titulo="Excluir item"
  mensagem="Esta ação é permanente e não pode ser desfeita."
  perigoso={true}
/>
```

### Com Carregamento
```jsx
<ModalConfirmacao
  aberto={true}
  titulo="Processando..."
  carregando={true}
  aoConfirmar={handleSave}
/>
```

## Implementação Técnica

- **`<dialog>` nativo**: Suporte a ESC para fechar, backdrop automático
- **showModal()**: Abre o modal com backdrop
- **close()**: Fecha o modal
- **Acessibilidade**: Semântico, focusável, suporta teclado
- **Responsive**: Funciona em mobile e desktop
