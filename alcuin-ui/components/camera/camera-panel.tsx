"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { apiFetch } from "@/lib/api"
import { Spinner } from "@/components/ui/spinner"

const REFRESH_MS = 3000

export function CameraPanel() {
  const [src, setSrc] = useState<string | null>(null)
  const [error, setError] = useState(false)
  const prevUrl = useRef<string | null>(null)

  const refresh = useCallback(async () => {
    try {
      const resp = await apiFetch("/api/v1/camera/snapshot")
      if (!resp.ok) { setError(true); return }
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      setSrc((prev) => {
        if (prev) URL.revokeObjectURL(prev)
        return url
      })
      prevUrl.current = url
      setError(false)
    } catch {
      setError(true)
    }
  }, [])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, REFRESH_MS)
    return () => {
      clearInterval(id)
      if (prevUrl.current) URL.revokeObjectURL(prevUrl.current)
    }
  }, [refresh])

  if (error) {
    return (
      <div className="flex h-48 items-center justify-center p-4 text-sm text-muted-foreground">
        Camera unavailable
      </div>
    )
  }

  if (!src) {
    return (
      <div className="flex h-48 items-center justify-center p-4">
        <Spinner className="h-6 w-6" />
      </div>
    )
  }

  return (
    <div className="p-3">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt="Live camera feed" className="w-full rounded-lg border border-border object-contain" />
      <p className="mt-2 text-center text-xs text-muted-foreground">Live · refreshes every 3s</p>
    </div>
  )
}
