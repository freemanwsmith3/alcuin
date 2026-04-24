"use client"

import { useState, useEffect, useRef, useCallback } from "react"
import { useChatContext } from "@/lib/chat-context"
import { apiFetch } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Spinner } from "@/components/ui/spinner"
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts"
import { Camera, RefreshCw } from "lucide-react"
import type { CameraReading } from "@/lib/types"

const REFRESH_MS = 3000

function LiveSnapshot() {
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
      <div className="flex h-48 items-center justify-center rounded-lg border border-border bg-secondary text-sm text-muted-foreground">
        Camera unavailable
      </div>
    )
  }
  if (!src) {
    return (
      <div className="flex h-48 items-center justify-center rounded-lg border border-border bg-secondary">
        <Spinner className="h-6 w-6" />
      </div>
    )
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt="Live camera feed" className="w-full rounded-lg border border-border object-contain" />
  )
}

function ReadingsChart({ readings }: { readings: CameraReading[] }) {
  const numeric = readings.filter((r) => r.value !== null)
  if (numeric.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No numeric readings yet. Use &quot;Analyze Now&quot; with a measurement question to start tracking.
      </p>
    )
  }

  const data = numeric.map((r) => ({
    time: new Date(r.captured_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    value: r.value,
    notes: r.notes ?? "",
  }))

  const unit = readings.find((r) => r.unit)?.unit ?? ""

  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
        <XAxis dataKey="time" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} />
        <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} unit={unit ? ` ${unit}` : ""} />
        <Tooltip
          contentStyle={{ background: "hsl(var(--card))", border: "1px solid hsl(var(--border))", borderRadius: 6 }}
          labelStyle={{ color: "hsl(var(--foreground))", fontSize: 12 }}
          formatter={(v: number, _name: string, item) => [
            `${v}${unit ? ` ${unit}` : ""}`,
            (item.payload as { notes?: string })?.notes || "value",
          ]}
        />
        <Line type="monotone" dataKey="value" stroke="#8b5cf6" strokeWidth={2} dot={{ r: 3 }} />
      </LineChart>
    </ResponsiveContainer>
  )
}

export function CameraPanel() {
  const { cameraReadings, analyzeCamera, fetchCameraReadings } = useChatContext()
  const [question, setQuestion] = useState(
    `Estimate what percentage of the jar is filled. Return JSON: {"value": <0-100>, "unit": "pct", "label": "fill level", "notes": "<observations>"}`
  )
  const [storeImage, setStoreImage] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => { fetchCameraReadings() }, [fetchCameraReadings])

  const handleAnalyze = async () => {
    if (!question.trim()) return
    setLoading(true)
    setError("")
    const err = await analyzeCamera(question, storeImage)
    if (err) setError(err)
    setLoading(false)
  }

  return (
    <div className="flex flex-col p-6 gap-6">
      {/* Live feed */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">1</div>
          <h2 className="text-sm font-semibold">Live Feed</h2>
          <span className="text-xs text-muted-foreground">refreshes every 3s</span>
        </div>
        <LiveSnapshot />
      </div>

      {/* Analyze */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">2</div>
          <h2 className="text-sm font-semibold">Analyze</h2>
        </div>
        <Textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="What should Claude look for or measure?"
          className="min-h-[80px] resize-none text-sm"
          disabled={loading}
        />
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Switch id="store-img" checked={storeImage} onCheckedChange={setStoreImage} />
            <Label htmlFor="store-img" className="text-xs text-muted-foreground">Save image to storage</Label>
          </div>
          <Button onClick={handleAnalyze} disabled={loading || !question.trim()} className="gap-2">
            {loading ? <Spinner className="h-4 w-4" /> : <Camera className="h-4 w-4" />}
            Analyze Now
          </Button>
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
      </div>

      {/* Chart */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">3</div>
          <h2 className="text-sm font-semibold">Analytics</h2>
          {cameraReadings.length > 0 && (
            <span className="text-xs text-muted-foreground">{cameraReadings.length} readings</span>
          )}
          <button onClick={fetchCameraReadings} className="ml-auto text-muted-foreground hover:text-foreground">
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>
        <ReadingsChart readings={cameraReadings} />
        {cameraReadings.length > 0 && (
          <div className="flex flex-col gap-1">
            {[...cameraReadings].reverse().slice(0, 3).map((r) => (
              <div key={r.id} className="flex items-start gap-2 text-xs text-muted-foreground">
                <span className="shrink-0 font-mono">
                  {new Date(r.captured_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                </span>
                <span className="flex-1">{r.notes ?? r.label ?? "—"}</span>
                {r.value !== null && (
                  <span className="shrink-0 font-medium text-foreground">
                    {r.value}{r.unit ? ` ${r.unit}` : ""}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
