"use client"

import { ChatProvider, useChatContext } from "@/lib/chat-context"
import { AuthOverlay } from "./auth-overlay"
import { ChatSidebar } from "./chat-sidebar"
import { ChatHeader } from "./chat-header"
import { MessageList } from "./message-list"
import { ChatInput } from "./chat-input"
import { GraphPanel } from "@/components/graph/graph-panel"

function ChatLayout() {
  const { view } = useChatContext()

  return (
    <div className="flex h-screen bg-background">
      <aside className="hidden w-80 shrink-0 border-r border-border lg:block">
        <ChatSidebar />
      </aside>

      <main className="flex flex-1 flex-col overflow-hidden">
        <ChatHeader />
        {view === "graph" ? (
          <GraphPanel />
        ) : (
          <>
            <MessageList />
            <ChatInput />
          </>
        )}
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
