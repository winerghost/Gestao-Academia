'use client'
import { useState, useEffect } from 'react'

export function useToast() {
  const [toast, setToast] = useState(null)

  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => setToast(null), 3500)
    return () => clearTimeout(timer)
  }, [toast])

  return {
    toast,
    show: (message, type = 'success') => setToast({ message, type }),
    dismiss: () => setToast(null),
  }
}
