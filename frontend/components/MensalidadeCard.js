import StatusBadge from './StatusBadge'

export default function MensalidadeCard({ mensalidade }) {
  const { valor, juros, valor_total, data_vencimento, data_pagamento, status, aluno_planos } = mensalidade
  const plano = aluno_planos?.planos?.nome ?? '—'

  return (
    <div className="bg-white border border-gray-100 rounded-xl p-4 shadow-sm">
      <div className="flex items-center justify-between mb-3">
        <span className="font-medium text-gray-800">{plano}</span>
        <StatusBadge status={status} />
      </div>

      <div className="space-y-1.5 text-sm">
        <Row label="Vencimento" value={data_vencimento} />
        <Row label="Valor"      value={`R$ ${Number(valor).toFixed(2)}`} />
        {juros > 0 && (
          <Row label="Juros (2% a.m.)" value={`R$ ${Number(juros).toFixed(2)}`} vermelho />
        )}
        <div className="border-t pt-1.5 mt-1">
          <Row label="Total" value={`R$ ${Number(valor_total).toFixed(2)}`} negrito />
        </div>
        {data_pagamento && (
          <Row label="Pago em" value={data_pagamento} verde />
        )}
      </div>
    </div>
  )
}

function Row({ label, value, vermelho, verde, negrito }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-500">{label}</span>
      <span className={`${vermelho ? 'text-red-500' : verde ? 'text-green-600' : 'text-gray-700'} ${negrito ? 'font-semibold' : ''}`}>
        {value}
      </span>
    </div>
  )
}
