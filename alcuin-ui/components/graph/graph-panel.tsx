"use client"

import { useState } from "react"
import { useChatContext } from "@/lib/chat-context"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Spinner } from "@/components/ui/spinner"
import { DataTable } from "./data-table"
import { ForceGraph } from "./force-graph"
import { Sparkles, GitBranch } from "lucide-react"

export function GraphPanel() {
  const { graphSchema, graphData, graphLoading, useGraph, setUseGraph, generateGraphData, buildGraph } = useChatContext()
  const [prompt, setPrompt] = useState("")
  const [error, setError] = useState("")

  const handleGenerate = async () => {
    if (!prompt.trim()) return
    setError("")
    const err = await generateGraphData(prompt)
    if (err) setError(err)
  }

  const handleBuild = async () => {
    setError("")
    const err = await buildGraph()
    if (err) setError(err)
  }

  return (
    <div className="flex flex-1 flex-col overflow-y-auto p-6 gap-6">
      {/* Step 1: Generate */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">1</div>
          <h2 className="text-sm font-semibold">Generate Fake Data</h2>
        </div>
        <p className="text-xs text-muted-foreground">
          Describe a dataset and the AI will generate realistic relational data for you.
        </p>
        <Textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g. A tech company with 20 employees, departments, and reporting relationships"
          className="min-h-[80px] resize-none text-sm"
          disabled={graphLoading}
        />
        <Button onClick={handleGenerate} disabled={graphLoading || !prompt.trim()} className="w-fit gap-2">
          {graphLoading && !graphSchema ? <Spinner className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
          Generate Data
        </Button>
      </div>

      {/* Step 2: View Table */}
      {graphSchema && (
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">2</div>
            <h2 className="text-sm font-semibold">Generated Data</h2>
            <span className="text-xs text-muted-foreground">({graphSchema.tables.length} tables, {graphSchema.tables.reduce((s, t) => s + t.rows.length, 0)} rows)</span>
          </div>
          <div className="pb-2">
            <DataTable schema={graphSchema} />
          </div>
          <Button onClick={handleBuild} disabled={graphLoading} variant="outline" className="w-fit gap-2">
            {graphLoading && graphSchema && !graphData ? <Spinner className="h-4 w-4" /> : <GitBranch className="h-4 w-4" />}
            Build Knowledge Graph
          </Button>
        </div>
      )}

      {/* Step 3: Visualize */}
      {graphData && (
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground text-xs font-bold">3</div>
            <h2 className="text-sm font-semibold">Knowledge Graph</h2>
            <span className="text-xs text-muted-foreground">({graphData.nodes.length} nodes, {graphData.edges.length} edges)</span>
          </div>
          <ForceGraph data={graphData} />

          <div className="flex items-center justify-between rounded-md border border-border bg-card p-3">
            <div className="flex flex-col gap-0.5">
              <Label className="text-sm font-medium">Use Graph in Chat</Label>
              <p className="text-xs text-muted-foreground">The chatbot will query this graph to answer your questions</p>
            </div>
            <Switch checked={useGraph} onCheckedChange={setUseGraph} />
          </div>
        </div>
      )}

      {error && <p className="text-sm text-destructive">{error}</p>}
    </div>
  )
}
