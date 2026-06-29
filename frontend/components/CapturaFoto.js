'use client'
import { useEffect, useRef, useState } from 'react'

// Componente reutilizável de foto: preview + captura por webcam + envio de
// arquivo. É "controlado": `value` é a foto atual (data URL OU URL http) e
// `onChange(dataUrlOuNull)` é chamado ao capturar/enviar (data URL) ou remover (null).
// O backend revalida e re-encoda tudo — aqui a validação é só de UX.

const TIPOS = ['image/jpeg', 'image/png', 'image/webp']
const MAX = 4 * 1024 * 1024 // 4 MB

function iniciais(nome = '') {
  return nome.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase() || '?'
}

export default function CapturaFoto({ value, onChange, nome = '', disabled = false }) {
  const videoRef = useRef(null)
  const fileRef = useRef(null)
  const [stream, setStream] = useState(null)
  const [erro, setErro] = useState('')

  // Liga o stream ao <video> e garante que a câmera é desligada ao desmontar.
  useEffect(() => {
    if (stream && videoRef.current) videoRef.current.srcObject = stream
    return () => { if (stream) stream.getTracks().forEach(t => t.stop()) }
  }, [stream])

  async function abrirCamera() {
    setErro('')
    try {
      const s = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user' }, audio: false,
      })
      setStream(s)
    } catch {
      setErro('Não foi possível acessar a câmera. Verifique a permissão ou envie um arquivo.')
    }
  }

  function pararCamera() {
    if (stream) stream.getTracks().forEach(t => t.stop())
    setStream(null)
  }

  function capturar() {
    const v = videoRef.current
    if (!v || !v.videoWidth) return
    const lado = Math.min(v.videoWidth, v.videoHeight)
    const c = document.createElement('canvas')
    c.width = lado; c.height = lado
    const ctx = c.getContext('2d')
    // Recorte quadrado central (mesmo aspecto que o backend gera).
    const sx = (v.videoWidth - lado) / 2
    const sy = (v.videoHeight - lado) / 2
    ctx.drawImage(v, sx, sy, lado, lado, 0, 0, lado, lado)
    const dataUrl = c.toDataURL('image/jpeg', 0.85)
    pararCamera()
    onChange(dataUrl)
  }

  function aoArquivo(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setErro('')
    if (!TIPOS.includes(file.type)) { setErro('Use JPG, PNG ou WEBP.'); return }
    if (file.size > MAX) { setErro('Imagem grande demais (máx. 4 MB).'); return }
    const reader = new FileReader()
    reader.onload = () => onChange(reader.result)
    reader.readAsDataURL(file)
  }

  // Modo câmera aberta: mostra o vídeo ao vivo + ações de capturar/cancelar.
  if (stream) {
    return (
      <div className="flex flex-col gap-2">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="w-40 h-40 rounded-xl object-cover bg-black"
          style={{ transform: 'scaleX(-1)' }}
        />
        <div className="flex gap-2">
          <button type="button" onClick={capturar}
            className="text-white px-4 py-2 rounded-lg text-sm font-medium transition"
            style={{ backgroundColor: 'var(--cor-destaque)' }}>
            📸 Capturar
          </button>
          <button type="button" onClick={pararCamera}
            className="px-4 py-2 rounded-lg text-sm font-medium border border-gray-200 text-gray-600 hover:bg-gray-50 transition">
            Cancelar
          </button>
        </div>
        {erro && <p className="text-xs text-red-500">{erro}</p>}
      </div>
    )
  }

  return (
    <div className="flex items-start gap-4">
      {/* Preview */}
      {value ? (
        // eslint-disable-next-line @next/next/no-img-element -- avatar pequeno, URL remota/data URL; next/image exigiria remotePatterns sem ganho real
        <img src={value} alt="Foto" className="w-24 h-24 rounded-full object-cover flex-shrink-0 border border-gray-200" />
      ) : (
        <div className="w-24 h-24 rounded-full flex items-center justify-center text-2xl font-bold text-white flex-shrink-0"
          style={{ backgroundColor: 'var(--cor-destaque)' }}>
          {iniciais(nome)}
        </div>
      )}

      <div className="flex-1 min-w-0">
        <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp"
          className="hidden" onChange={aoArquivo} />
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={abrirCamera} disabled={disabled}
            className="text-white px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-60"
            style={{ backgroundColor: 'var(--cor-destaque)' }}>
            📷 {value ? 'Tirar outra' : 'Tirar foto'}
          </button>
          <button type="button" onClick={() => fileRef.current?.click()} disabled={disabled}
            className="px-4 py-2 rounded-lg text-sm font-medium border border-gray-200 text-gray-700 hover:bg-gray-50 transition disabled:opacity-60">
            Enviar arquivo
          </button>
          {value && (
            <button type="button" onClick={() => onChange(null)} disabled={disabled}
              className="px-4 py-2 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50 transition disabled:opacity-60">
              Remover
            </button>
          )}
        </div>
        <p className="text-xs text-gray-400 mt-2">
          Webcam ou arquivo (JPG, PNG, WEBP até 4 MB). Recortada em quadrado.
        </p>
        {erro && <p className="text-xs text-red-500 mt-1">{erro}</p>}
      </div>
    </div>
  )
}
