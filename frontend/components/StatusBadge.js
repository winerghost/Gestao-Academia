const cores = {
  ativo:        'bg-green-50 text-green-700',
  inativo:      'bg-gray-100 text-gray-500',
  inadimplente: 'bg-red-50 text-red-600',
  paga:         'bg-green-50 text-green-700',
  pendente:     'bg-yellow-50 text-yellow-700',
  atrasada:     'bg-red-50 text-red-600',
}

export default function StatusBadge({ status }) {
  const label = status.charAt(0).toUpperCase() + status.slice(1)
  return (
    <span className={`inline-flex items-center text-xs font-semibold px-2.5 py-0.5 rounded-full ${cores[status] ?? 'bg-gray-100 text-gray-500'}`}>
      {label}
    </span>
  )
}
