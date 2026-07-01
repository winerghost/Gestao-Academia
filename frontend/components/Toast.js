'use client'

export default function Toast({ message, type = 'success' }) {
  if (!message) return null

  const bgColor = type === 'success' ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
  const textColor = type === 'success' ? 'text-green-800' : 'text-red-800'
  const iconBg = type === 'success' ? 'bg-green-100' : 'bg-red-100'
  const iconText = type === 'success' ? 'text-green-600' : 'text-red-600'
  const icon = type === 'success' ? '✓' : '⚠'

  return (
    <div className={`fixed top-4 right-4 ${bgColor} border rounded-lg px-4 py-3 shadow-lg animate-slideIn`}>
      <div className="flex items-start gap-3">
        <div className={`${iconBg} ${iconText} w-6 h-6 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0`}>
          {icon}
        </div>
        <p className={`${textColor} text-sm font-medium`}>{message}</p>
      </div>

      <style jsx>{`
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateX(400px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
        .animate-slideIn {
          animation: slideIn 0.3s ease-out;
        }
      `}</style>
    </div>
  )
}
