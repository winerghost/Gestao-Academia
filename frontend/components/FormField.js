'use client'

export default function FormField({ label, error, required, hint, children, className = '' }) {
  return (
    <div className={className}>
      {label && (
        <label className="block text-sm font-medium text-gray-700 mb-1">
          {label}{required && <span className="text-orange-500"> *</span>}
        </label>
      )}
      {children}
      {error ? (
        <p className="text-xs text-red-600 mt-1">{error}</p>
      ) : hint ? (
        <p className="text-xs text-gray-400 mt-1">{hint}</p>
      ) : null}
    </div>
  )
}

export function inputClass(hasError) {
  return `w-full border rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:border-transparent bg-white transition ${
    hasError ? 'border-red-300 ring-1 ring-red-200 focus:ring-red-400' : 'border-gray-200 focus:ring-orange-500'
  }`
}
