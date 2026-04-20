"use client"

import dynamic from "next/dynamic"
import { useRef, useCallback } from "react"
import type { GraphData } from "@/lib/types"

const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), { ssr: false })

const GROUP_COLORS: Record<string, string> = {}
const PALETTE = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"]
let colorIdx = 0

function groupColor(group: string): string {
  if (!GROUP_COLORS[group]) {
    GROUP_COLORS[group] = PALETTE[colorIdx % PALETTE.length]
    colorIdx++
  }
  return GROUP_COLORS[group]
}

export function ForceGraph({ data }: { data: GraphData }) {
  const graphData = {
    nodes: data.nodes.map((n) => ({ ...n, color: groupColor(n.group) })),
    links: data.edges.map((e) => ({ source: e.source, target: e.target, label: e.label })),
  }

  const paintNode = useCallback((node: Record<string, unknown>, ctx: CanvasRenderingContext2D) => {
    const x = node.x as number
    const y = node.y as number
    const color = node.color as string
    const label = node.label as string

    ctx.beginPath()
    ctx.arc(x, y, 6, 0, 2 * Math.PI)
    ctx.fillStyle = color
    ctx.fill()

    ctx.font = "4px sans-serif"
    ctx.fillStyle = "white"
    ctx.textAlign = "center"
    ctx.textBaseline = "middle"
    ctx.fillText(label.length > 12 ? label.slice(0, 12) + "…" : label, x, y + 12)
  }, [])

  return (
    <div className="rounded-md border bg-background overflow-hidden" style={{ height: 420 }}>
      <ForceGraph2D
        graphData={graphData}
        nodeCanvasObject={paintNode as never}
        nodeCanvasObjectMode={() => "replace"}
        linkLabel="label"
        linkColor={() => "#6b7280"}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        backgroundColor="transparent"
        width={undefined}
        height={420}
      />
    </div>
  )
}
