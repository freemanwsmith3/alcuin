"use client"

import { ChatProvider } from "@/lib/chat-context"
import { AuthOverlay } from "./auth-overlay"
import { ChatSidebar } from "./chat-sidebar"
import { ChatHeader } from "./chat-header"
import { MessageList } from "./message-list"
import { ChatInput } from "./chat-input"

function ChatLayout() {
  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar - Hidden on mobile */}
      <aside className="hidden w-80 shrink-0 border-r border-border lg:block">
        <ChatSidebar />
      </aside>

      {/* Main content */}
      <main className="flex flex-1 flex-col overflow-hidden">
        <ChatHeader />
        <MessageList />
        <ChatInput />
      </main>

      {/* Auth overlay */}
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
