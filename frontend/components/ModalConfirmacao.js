'use client'
import { useEffect, useRef } from 'react'

export default function ModalConfirmacao({
  aberto = false,
  titulo = 'Confirmar ação',
  mensagem = 'Tem certeza que deseja continuar?',
  botaoConfirmar = 'Confirmar',
  botaoCancelar = 'Cancelar',
  perigoso = false,
  aoConfirmar = () => {},
  aoCancelar = () => {},
  carregando = false,
}) {
  const dialogRef = useRef(null)

  useEffect(() => {
    if (aberto) {
      dialogRef.current?.showModal()
    } else {
      dialogRef.current?.close()
    }
  }, [aberto])

  const handleConfirmar = () => {
    aoConfirmar()
  }

  const handleCancelar = () => {
    dialogRef.current?.close()
    aoCancelar()
  }

  const handleBackdropClick = (e) => {
    if (e.target === dialogRef.current) {
      handleCancelar()
    }
  }

  return (
    <dialog
      ref={dialogRef}
      onClick={handleBackdropClick}
      className="rounded-xl shadow-2xl backdrop:bg-black/30 max-w-sm w-full mx-auto p-0 border-0"
    >
      <div className="p-6">
        {/* Ícone decorativo */}
        <div className={`w-12 h-12 rounded-full flex items-center justify-center mb-4 ${
          perigoso ? 'bg-red-50' : 'bg-blue-50'
        }`}>
          <span className={`text-xl ${perigoso ? 'text-red-600' : 'text-blue-600'}`}>
            {perigoso ? '⚠' : 'ℹ'}
          </span>
        </div>

        {/* Título */}
        <h2 className="text-lg font-bold text-gray-900 mb-2">{titulo}</h2>

        {/* Mensagem */}
        <p className="text-sm text-gray-600 mb-6 leading-relaxed">{mensagem}</p>

        {/* Botões */}
        <div className="flex gap-3 justify-end">
          <button
            onClick={handleCancelar}
            disabled={carregando}
            className="px-4 py-2 rounded-lg text-sm font-medium border border-gray-200 text-gray-700 hover:bg-gray-50 transition disabled:opacity-60"
          >
            {botaoCancelar}
          </button>
          <button
            onClick={handleConfirmar}
            disabled={carregando}
            className={`px-4 py-2 rounded-lg text-sm font-medium text-white transition disabled:opacity-60 ${
              perigoso
                ? 'bg-red-600 hover:bg-red-700'
                : 'bg-orange-500 hover:bg-orange-600'
            }`}
          >
            {carregando ? '...' : botaoConfirmar}
          </button>
        </div>
      </div>
    </dialog>
  )
}
