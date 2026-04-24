"use client"

import { useChatContext } from "@/lib/chat-context"
import { ForceGraph } from "./force-graph"
import { GitBranch } from "lucide-react"

export function GraphPanel() {
  const { graphData } = useChatContext()

  if (!graphData) {
    return (
      <div className="flex h-48 flex-col items-center justify-center gap-2 p-4 text-center text-sm text-muted-foreground">
        <GitBranch className="h-6 w-6 opacity-40" />
        <p>No graph yet. Ask the assistant to build one.</p>
      </div>
    )
  }

  return (
    <div className="p-3">
      <ForceGraph data={graphData} />
      <p className="mt-2 text-center text-xs text-muted-foreground">
        {graphData.nodes.length} nodes · {graphData.edges.length} edges
      </p>
    </div>
  )
}
