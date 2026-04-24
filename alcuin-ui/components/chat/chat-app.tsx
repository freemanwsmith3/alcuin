"use client"

import { ChatProvider, useChatContext } from "@/lib/chat-context"
import { AuthOverlay } from "./auth-overlay"
import { ChatSidebar } from "./chat-sidebar"
import { ChatHeader } from "./chat-header"
import { MessageList } from "./message-list"
import { ChatInput } from "./chat-input"
import { GraphPanel } from "@/components/graph/graph-panel"
import { CameraPanel } from "@/components/camera/camera-panel"
import { Camera, Network, X } from "lucide-react"

function SidePanel() {
  const { showGraph, setShowGraph, showCamera, setShowCamera } = useChatContext()

  if (!showGraph && !showCamera) return null

  return (
    <div className="hidden lg:flex w-[420px] shrink-0 flex-col border-l border-border overflow-hidden">
      {showCamera && (
        <div className={`flex flex-col border-b border-border ${showGraph ? "h-1/2" : "flex-1"}`}>
          <div className="flex h-10 shrink-0 items-center justify-between border-b border-border bg-secondary/50 px-4">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Camera className="h-4 w-4" />
              Camera
            </div>
            <button onClick={() => setShowCamera(false)} className="text-muted-foreground hover:text-foreground">
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            <CameraPanel />
          </div>
        </div>
      )}

      {showGraph && (
        <div className={`flex flex-col ${showCamera ? "h-1/2" : "flex-1"}`}>
          <div className="flex h-10 shrink-0 items-center justify-between border-b border-border bg-secondary/50 px-4">
            <div className="flex items-center gap-2 text-sm font-medium">
              <Network className="h-4 w-4" />
              Graph
            </div>
            <button onClick={() => setShowGraph(false)} className="text-muted-foreground hover:text-foreground">
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto">
            <GraphPanel />
          </div>
        </div>
      )}
    </div>
  )
}

function ChatLayout() {
  return (
    <div className="flex h-screen bg-background">
      <aside className="hidden w-80 shrink-0 border-r border-border lg:block">
        <ChatSidebar />
      </aside>

      <main className="flex flex-1 overflow-hidden">
        <div className="flex flex-1 flex-col overflow-hidden">
          <ChatHeader />
          <MessageList />
          <ChatInput />
        </div>
        <SidePanel />
      </main>

      <AuthOverlay />
    </div>
  )
}

export function ChatApp({ company }: { company?: string }) {
  return (
    <ChatProvider company={company ?? null}>
      <ChatLayout />
    </ChatProvider>
  )
}
