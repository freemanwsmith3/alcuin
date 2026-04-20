"use client"

import { useRef } from "react"
import { useChatContext } from "@/lib/chat-context"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import type { Model, DocumentStatus } from "@/lib/types"
import {
  FileText,
  LogOut,
  MessageSquare,
  Network,
  Plus,
  Upload,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
} from "lucide-react"

const models: { value: Model; label: string }[] = [
  { value: "claude-opus-4-5", label: "Claude Opus 4.5" },
  { value: "claude-sonnet-4-5", label: "Claude Sonnet 4.5" },
  { value: "claude-haiku-4-5", label: "Claude Haiku 4.5" },
  { value: "gpt-4o", label: "GPT-4o" },
  { value: "gpt-4o-mini", label: "GPT-4o Mini" },
]

function getStatusBadge(status: DocumentStatus) {
  switch (status) {
    case "pending":
      return (
        <Badge variant="secondary" className="gap-1 text-xs">
          <Clock className="h-3 w-3" />
          Pending
        </Badge>
      )
    case "processing":
      return (
        <Badge variant="secondary" className="gap-1 bg-info/20 text-info text-xs">
          <Loader2 className="h-3 w-3 animate-spin" />
          Processing
        </Badge>
      )
    case "ready":
      return (
        <Badge variant="secondary" className="gap-1 bg-success/20 text-success text-xs">
          <CheckCircle2 className="h-3 w-3" />
          Ready
        </Badge>
      )
    case "failed":
      return (
        <Badge variant="destructive" className="gap-1 text-xs">
          <XCircle className="h-3 w-3" />
          Failed
        </Badge>
      )
  }
}

export function ChatSidebar() {
  const {
    user,
    logout,
    sessionId,
    newSession,
    documents,
    uploadDocument,
    toggleDocument,
    settings,
    updateSettings,
    company,
    view,
    setView,
  } = useChatContext()

  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files) {
      Array.from(files).forEach((file) => {
        if (file.type === "application/pdf") {
          uploadDocument(file)
        }
      })
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = ""
    }
  }

  return (
    <div className="flex h-full flex-col bg-sidebar">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-sidebar-border p-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-sidebar-accent">
          <MessageSquare className="h-5 w-5 text-sidebar-foreground" />
        </div>
        <div className="flex-1 min-w-0">
          <h1 className="text-sm font-semibold text-sidebar-foreground truncate">{company ?? "Alcuin"}</h1>
          <p className="text-xs text-muted-foreground">AI Chat Assistant</p>
        </div>
      </div>

      {/* View toggle */}
      <div className="flex border-b border-sidebar-border">
        <button
          onClick={() => setView("chat")}
          className={`flex flex-1 items-center justify-center gap-1.5 py-2 text-xs font-medium transition-colors ${view === "chat" ? "border-b-2 border-primary text-foreground" : "text-muted-foreground hover:text-foreground"}`}
        >
          <MessageSquare className="h-3.5 w-3.5" /> Chat
        </button>
        <button
          onClick={() => setView("graph")}
          className={`flex flex-1 items-center justify-center gap-1.5 py-2 text-xs font-medium transition-colors ${view === "graph" ? "border-b-2 border-primary text-foreground" : "text-muted-foreground hover:text-foreground"}`}
        >
          <Network className="h-3.5 w-3.5" /> Graph
        </button>
      </div>

      <ScrollArea className="flex-1">
        <div className="flex flex-col gap-6 p-4">
          {/* Model Selection */}
          <div className="flex flex-col gap-2">
            <Label className="text-xs font-medium text-muted-foreground">Model</Label>
            <Select
              value={settings.model}
              onValueChange={(value: Model) => updateSettings({ model: value })}
            >
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {models.map((model) => (
                  <SelectItem key={model.value} value={model.value}>
                    {model.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Temperature */}
          <div className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <Label className="text-xs font-medium text-muted-foreground">Temperature</Label>
              <span className="text-xs font-mono text-foreground">{settings.temperature.toFixed(2)}</span>
            </div>
            <Slider
              value={[settings.temperature]}
              onValueChange={([value]) => updateSettings({ temperature: value })}
              min={0}
              max={1}
              step={0.01}
              className="w-full"
            />
          </div>

          {/* System Prompt */}
          <div className="flex flex-col gap-2">
            <Label className="text-xs font-medium text-muted-foreground">System Prompt</Label>
            <Textarea
              value={settings.systemPrompt}
              onChange={(e) => updateSettings({ systemPrompt: e.target.value })}
              placeholder="Enter system prompt..."
              className="min-h-[80px] resize-none text-sm"
            />
          </div>

          {/* Stream Response */}
          <div className="flex items-center justify-between">
            <Label className="text-xs font-medium text-muted-foreground">Stream Response</Label>
            <Switch
              checked={settings.streamResponse}
              onCheckedChange={(checked) => updateSettings({ streamResponse: checked })}
            />
          </div>

          <Separator className="bg-sidebar-border" />

          {/* Document Upload */}
          <div className="flex flex-col gap-3">
            <Label className="text-xs font-medium text-muted-foreground">RAG Documents</Label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf"
              multiple
              onChange={handleFileUpload}
              className="hidden"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              className="w-full gap-2"
            >
              <Upload className="h-4 w-4" />
              Upload PDF
            </Button>

            {/* Document List */}
            {documents.length > 0 && (
              <div className="flex flex-col gap-2">
                {documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-start gap-2 rounded-md border border-sidebar-border bg-sidebar-accent/50 p-2"
                  >
                    <Checkbox
                      id={doc.id}
                      checked={doc.selected}
                      onCheckedChange={() => toggleDocument(doc.id)}
                      disabled={doc.status !== "ready"}
                      className="mt-0.5"
                    />
                    <div className="flex flex-1 flex-col gap-1 min-w-0">
                      <label
                        htmlFor={doc.id}
                        className="flex items-center gap-2 text-xs text-foreground cursor-pointer"
                      >
                        <FileText className="h-3 w-3 shrink-0" />
                        <span className="truncate">{doc.name}</span>
                      </label>
                      {getStatusBadge(doc.status)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <Separator className="bg-sidebar-border" />

          {/* Session Info */}
          <div className="flex flex-col gap-3">
            <Label className="text-xs font-medium text-muted-foreground">Session</Label>
            <div className="rounded-md border border-sidebar-border bg-sidebar-accent/50 p-2">
              <p className="break-all font-mono text-[10px] text-muted-foreground">{sessionId}</p>
            </div>
            <Button variant="outline" size="sm" onClick={newSession} className="w-full gap-2">
              <Plus className="h-4 w-4" />
              New Session
            </Button>
          </div>
        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="border-t border-sidebar-border p-4">
        <Button
          variant="ghost"
          size="sm"
          onClick={logout}
          className="w-full justify-start gap-2 text-muted-foreground hover:text-foreground"
        >
          <LogOut className="h-4 w-4" />
          <span className="truncate">{user?.username}</span>
        </Button>
      </div>
    </div>
  )
}
