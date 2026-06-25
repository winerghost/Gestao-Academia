const cores = {
  ativo:        'bg-green-100 text-green-800',
  inativo:      'bg-gray-100 text-gray-500',
  inadimplente: 'bg-red-100 text-red-700',
  paga:         'bg-green-100 text-green-800',
  pendente:     'bg-yellow-100 text-yellow-800',
  atrasada:     'bg-red-100 text-red-700',
}

export default function StatusBadge({ status }) {
  const label = status.charAt(0).toUpperCase() + status.slice(1)
  return (
    <span className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${cores[status] ?? 'bg-gray-100 text-gray-600'}`}>
      {label}
    </span>
  )
}
