'use client'
import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { useAuth } from '../../../../hooks/useAuth'
import {
  getMe, atualizarMe, trocarSenha,
  uploadAvatar, removerAvatar, usarGravatar,
} from '../../../../lib/api'
import FormField, { inputClass } from '@/components/FormField'
import Toast from '@/components/Toast'
import { useToast } from '@/hooks/useToast'

// Converte data URL (canvas.toDataURL) em File para reutilizar o upload multipart.
function dataUrlParaFile(dataUrl, nome = 'webcam.jpg') {
  const [header, b64] = dataUrl.split(',')
  const mime = header.match(/:(.*?);/)?.[1] || 'image/jpeg'
  const bin = atob(b64)
  const arr = new Uint8Array(bin.length)
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i)
  return new File([arr], nome, { type: mime })
}

const input = 'w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2'
const ring = { '--tw-ring-color': 'var(--cor-destaque)' }
const btn = 'text-white px-5 py-2 rounded-lg text-sm font-medium transition disabled:opacity-60'
const btnStyle = { backgroundColor: 'var(--cor-destaque)' }

// Tipos e tamanho aceitos no cliente (o backend revalida e re-encoda).
const AVATAR_TIPOS = ['image/jpeg', 'image/png', 'image/webp']
const AVATAR_MAX = 4 * 1024 * 1024 // 4 MB

function Aviso({ tipo, children }) {
  if (!children) return null
  const cor = tipo === 'erro'
    ? 'text-red-600 bg-red-50'
    : 'text-green-700 bg-green-50'
  return <p className={`text-sm rounded-lg px-3 py-2 ${cor}`}>{children}</p>
}

function iniciais(nome = '') {
  return nome.split(' ').map(w => w[0]).slice(0, 2).join('').toUpperCase() || 'GA'
}

// Mostra a foto; se a URL quebrar (ex.: Gravatar removido), cai nas iniciais.
function AvatarPreview({ url, nome }) {
  const [erro, setErro] = useState(false)
  // Reseta o erro quando a URL muda — ajuste de estado durante o render
  // (padrão recomendado do React; evita setState dentro de useEffect).
  const [urlAnterior, setUrlAnterior] = useState(url)
  if (url !== urlAnterior) {
    setUrlAnterior(url)
    setErro(false)
  }
  if (url && !erro) {
    return (
      // eslint-disable-next-line @next/next/no-img-element -- avatar pequeno, URL remota (Supabase/Gravatar); next/image exigiria remotePatterns sem ganho real
      <img
        src={url}
        alt="Foto de perfil"
        onError={() => setErro(true)}
        className="w-24 h-24 rounded-full object-cover flex-shrink-0"
        style={{ border: '1px solid var(--border-color)' }}
      />
    )
  }
  return (
    <div
      className="w-24 h-24 rounded-full flex items-center justify-center text-2xl font-bold text-white flex-shrink-0"
      style={{ backgroundColor: 'var(--cor-destaque)' }}
    >
      {iniciais(nome)}
    </div>
  )
}

export default function ContaPage() {
  const { token } = useAuth()
  const [loading, setLoading] = useState(true)

  // Perfil
  const [perfil, setPerfil] = useState({ nome: '', telefone: '' })
  const [salvandoPerfil, setSalvandoPerfil] = useState(false)
  const [msgPerfil, setMsgPerfil] = useState({ tipo: '', texto: '' })

  // Foto de perfil (avatar)
  const fileRef = useRef(null)
  const videoRef = useRef(null)
  const [avatarUrl, setAvatarUrl] = useState(null)
  const [avatarBusy, setAvatarBusy] = useState('') // '', 'upload', 'gravatar', 'remover'
  const [msgAvatar, setMsgAvatar] = useState({ tipo: '', texto: '' })
  const [cameraStream, setCameraStream] = useState(null)

  // Senha
  const [senha, setSenha] = useState({ senha_atual: '', senha_nova: '', confirmar: '' })
  const [senhaErrors, setSenhaErrors] = useState({})
  const [salvandoSenha, setSalvandoSenha] = useState(false)
  const [msgSenha, setMsgSenha] = useState({ tipo: '', texto: '' })
  const { toast, show } = useToast()

  useEffect(() => {
    if (!token) return
    async function init() {
      try {
        const me = await getMe(token)
        setPerfil({ nome: me.nome || '', telefone: me.telefone || '' })
        setAvatarUrl(me.avatar_url || null)
      } catch { /* layout trata */ }
      setLoading(false)
    }
    init()
  }, [token])

  // Vincula o stream ao <video> e desliga a câmera ao desmontar / parar.
  useEffect(() => {
    if (cameraStream && videoRef.current) videoRef.current.srcObject = cameraStream
    return () => { if (cameraStream) cameraStream.getTracks().forEach(t => t.stop()) }
  }, [cameraStream])

  async function abrirCamera() {
    setMsgAvatar({ tipo: '', texto: '' })
    try {
      const s = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' }, audio: false })
      setCameraStream(s)
    } catch {
      setMsgAvatar({ tipo: 'erro', texto: 'Não foi possível acessar a câmera. Verifique a permissão ou use o botão de arquivo.' })
    }
  }

  function fecharCamera() {
    if (cameraStream) cameraStream.getTracks().forEach(t => t.stop())
    setCameraStream(null)
  }

  async function capturarFoto() {
    const v = videoRef.current
    if (!v || !v.videoWidth) return
    const lado = Math.min(v.videoWidth, v.videoHeight)
    const c = document.createElement('canvas')
    c.width = lado; c.height = lado
    c.getContext('2d').drawImage(v, (v.videoWidth - lado) / 2, (v.videoHeight - lado) / 2, lado, lado, 0, 0, lado, lado)
    fecharCamera()
    const file = dataUrlParaFile(c.toDataURL('image/jpeg', 0.85))
    setAvatarBusy('upload')
    setMsgAvatar({ tipo: '', texto: '' })
    try {
      const { avatar_url } = await uploadAvatar(token, file)
      aplicarAvatar(avatar_url)
      setMsgAvatar({ tipo: 'ok', texto: 'Foto tirada com sucesso.' })
    } catch (err) {
      setMsgAvatar({ tipo: 'erro', texto: err.message })
    }
    setAvatarBusy('')
  }

  // Atualiza o estado local e avisa o layout (navbar/sidebar) em tempo real.
  function aplicarAvatar(url) {
    setAvatarUrl(url)
    window.dispatchEvent(new CustomEvent('avatar-atualizado', { detail: url }))
  }

  async function aoSelecionarArquivo(e) {
    const file = e.target.files?.[0]
    e.target.value = '' // permite reenviar o mesmo arquivo depois
    if (!file) return
    setMsgAvatar({ tipo: '', texto: '' })
    if (!AVATAR_TIPOS.includes(file.type)) {
      setMsgAvatar({ tipo: 'erro', texto: 'Formato inválido. Use JPG, PNG ou WEBP.' })
      return
    }
    if (file.size > AVATAR_MAX) {
      setMsgAvatar({ tipo: 'erro', texto: 'Imagem grande demais (máx. 4 MB).' })
      return
    }
    setAvatarBusy('upload')
    try {
      const { avatar_url } = await uploadAvatar(token, file)
      aplicarAvatar(avatar_url)
      setMsgAvatar({ tipo: 'ok', texto: 'Foto atualizada com sucesso.' })
    } catch (err) {
      setMsgAvatar({ tipo: 'erro', texto: err.message })
    }
    setAvatarBusy('')
  }

  async function aoUsarGravatar() {
    setMsgAvatar({ tipo: '', texto: '' })
    setAvatarBusy('gravatar')
    try {
      const { avatar_url } = await usarGravatar(token)
      aplicarAvatar(avatar_url)
      setMsgAvatar({ tipo: 'ok', texto: 'Gravatar aplicado como foto de perfil.' })
    } catch (err) {
      setMsgAvatar({ tipo: 'erro', texto: err.message })
    }
    setAvatarBusy('')
  }

  async function aoRemoverFoto() {
    setMsgAvatar({ tipo: '', texto: '' })
    setAvatarBusy('remover')
    try {
      await removerAvatar(token)
      aplicarAvatar(null)
      setMsgAvatar({ tipo: 'ok', texto: 'Foto removida.' })
    } catch (err) {
      setMsgAvatar({ tipo: 'erro', texto: err.message })
    }
    setAvatarBusy('')
  }

  async function salvarPerfil(e) {
    e.preventDefault()
    setSalvandoPerfil(true)
    setMsgPerfil({ tipo: '', texto: '' })
    try {
      await atualizarMe(token, { nome: perfil.nome, telefone: perfil.telefone })
      setMsgPerfil({ tipo: 'ok', texto: 'Perfil atualizado com sucesso.' })
    } catch (err) {
      setMsgPerfil({ tipo: 'erro', texto: err.message })
    }
    setSalvandoPerfil(false)
  }

  async function salvarSenha(e) {
    e.preventDefault()
    setMsgSenha({ tipo: '', texto: '' })
    setSenhaErrors({})
    if (senha.senha_nova !== senha.confirmar) {
      setMsgSenha({ tipo: 'erro', texto: 'A confirmação não confere com a nova senha.' })
      return
    }
    setSalvandoSenha(true)
    try {
      await trocarSenha(token, { senha_atual: senha.senha_atual, senha_nova: senha.senha_nova })
      show('Senha alterada com sucesso!', 'success')
      setSenha({ senha_atual: '', senha_nova: '', confirmar: '' })
    } catch (err) {
      setSenhaErrors(err.fields || {})
      setMsgSenha({ tipo: 'erro', texto: Object.keys(err.fields || {}).length ? '' : err.message })
      const first = Object.keys(err.fields || {})[0]
      if (first) document.getElementById(first)?.focus()
    }
    setSalvandoSenha(false)
  }

  if (loading) return <p className="text-gray-400">Carregando...</p>

  return (
    <div className="max-w-2xl">
      <Link href="/admin/configuracoes" className="text-sm text-gray-500 hover:text-gray-700">
        ‹ Voltar para Configurações
      </Link>
      <h1 className="text-2xl font-bold text-gray-800 mt-2 mb-6">Conta</h1>

      {/* Foto do perfil */}
      <div className="bg-white rounded-xl shadow-sm p-5 mb-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Foto do perfil</h2>
        <div className="flex flex-col sm:flex-row sm:items-center gap-5">
          <AvatarPreview url={avatarUrl} nome={perfil.nome} />

          <div className="flex-1 min-w-0">
            {/* input de arquivo escondido — disparado pelo botão */}
            <input
              ref={fileRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="hidden"
              onChange={aoSelecionarArquivo}
            />

            {cameraStream ? (
              /* Modo câmera: vídeo ao vivo + capturar/cancelar */
              <div className="flex flex-col gap-2">
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="w-36 h-36 rounded-xl object-cover bg-black"
                  style={{ transform: 'scaleX(-1)' }}
                />
                <div className="flex gap-2">
                  <button
                    type="button"
                    className={btn}
                    style={btnStyle}
                    onClick={capturarFoto}
                    disabled={!!avatarBusy}
                  >
                    📸 Capturar
                  </button>
                  <button
                    type="button"
                    className="px-5 py-2 rounded-lg text-sm font-medium border border-gray-200 text-gray-700 hover:bg-gray-50 transition"
                    onClick={fecharCamera}
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            ) : (
              /* Modo normal: botões de upload, câmera, gravatar e remoção */
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className={btn}
                  style={btnStyle}
                  disabled={!!avatarBusy}
                  onClick={() => fileRef.current?.click()}
                >
                  {avatarBusy === 'upload' ? 'Enviando...' : (avatarUrl ? 'Trocar foto' : 'Enviar foto')}
                </button>
                <button
                  type="button"
                  className="px-5 py-2 rounded-lg text-sm font-medium border border-gray-200 text-gray-700 hover:bg-gray-50 transition disabled:opacity-60"
                  disabled={!!avatarBusy}
                  onClick={abrirCamera}
                >
                  📷 Tirar foto
                </button>
                <button
                  type="button"
                  className="px-5 py-2 rounded-lg text-sm font-medium border border-gray-200 text-gray-700 hover:bg-gray-50 transition disabled:opacity-60"
                  disabled={!!avatarBusy}
                  onClick={aoUsarGravatar}
                >
                  {avatarBusy === 'gravatar' ? 'Buscando...' : 'Usar meu Gravatar'}
                </button>
                {avatarUrl && (
                  <button
                    type="button"
                    className="px-5 py-2 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50 transition disabled:opacity-60"
                    disabled={!!avatarBusy}
                    onClick={aoRemoverFoto}
                  >
                    {avatarBusy === 'remover' ? 'Removendo...' : 'Remover foto'}
                  </button>
                )}
              </div>
            )}

            <p className="text-xs text-gray-400 mt-2">
              JPG, PNG ou WEBP até 4 MB. A imagem é recortada em formato quadrado.
              O Gravatar usa a foto vinculada ao e-mail da sua conta.
            </p>
            <div className="mt-2"><Aviso tipo={msgAvatar.tipo}>{msgAvatar.texto}</Aviso></div>
          </div>
        </div>
      </div>

      {/* Perfil */}
      <div className="bg-white rounded-xl shadow-sm p-5 mb-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Perfil</h2>
        <form onSubmit={salvarPerfil} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="sm:col-span-2">
            <label className="text-xs text-gray-500 mb-1 block">Nome *</label>
            <input className={input} style={ring} required placeholder="Seu nome completo" value={perfil.nome}
              onChange={e => setPerfil(p => ({ ...p, nome: e.target.value }))} />
          </div>
          <div className="sm:col-span-2">
            <label className="text-xs text-gray-500 mb-1 block">Telefone</label>
            <input className={input} style={ring} value={perfil.telefone}
              placeholder="(11) 99999-9999"
              onChange={e => setPerfil(p => ({ ...p, telefone: e.target.value }))} />
          </div>
          <div className="sm:col-span-2 flex items-center gap-3">
            <button type="submit" className={btn} style={btnStyle} disabled={salvandoPerfil}>
              {salvandoPerfil ? 'Salvando...' : 'Salvar perfil'}
            </button>
            <Aviso tipo={msgPerfil.tipo}>{msgPerfil.texto}</Aviso>
          </div>
        </form>
      </div>

      {/* Senha */}
      <div className="bg-white rounded-xl shadow-sm p-5">
        <h2 className="text-sm font-semibold text-gray-700 mb-4">Alterar senha</h2>
        <form onSubmit={salvarSenha} className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <FormField label="Senha atual" required error={senhaErrors.senha_atual} className="sm:col-span-2">
            <input id="senha_atual" type="password" className={inputClass(!!senhaErrors.senha_atual)} required placeholder="Digite sua senha atual" value={senha.senha_atual}
              onChange={e => setSenha(s => ({ ...s, senha_atual: e.target.value }))} />
          </FormField>

          <FormField label="Nova senha" required error={senhaErrors.senha_nova}>
            <input id="senha_nova" type="password" className={inputClass(!!senhaErrors.senha_nova)} required placeholder="Mínimo 8 caracteres" value={senha.senha_nova}
              onChange={e => setSenha(s => ({ ...s, senha_nova: e.target.value }))} />
          </FormField>

          <FormField label="Confirmar nova senha" required error={senhaErrors.confirmar}>
            <input id="confirmar" type="password" className={inputClass(!!senhaErrors.confirmar)} required placeholder="Repita a nova senha" value={senha.confirmar}
              onChange={e => setSenha(s => ({ ...s, confirmar: e.target.value }))} />
          </FormField>

          <div className="sm:col-span-2 flex items-center gap-3">
            <button type="submit" className={btn} style={btnStyle} disabled={salvandoSenha}>
              {salvandoSenha ? 'Alterando...' : 'Alterar senha'}
            </button>
            <Aviso tipo={msgSenha.tipo}>{msgSenha.texto}</Aviso>
          </div>
        </form>
      </div>

      {toast && <Toast message={toast.message} type={toast.type} />}
    </div>
  )
}
