"use client"

import { useChatContext } from "@/lib/chat-context"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet"
import { ChatSidebar } from "./chat-sidebar"
import { Menu, MessageSquare, Database, Zap } from "lucide-react"

export function ChatHeader() {
  const { company, ragActive, isTyping, settings } = useChatContext()

  return (
    <header className="flex h-14 items-center justify-between border-b border-border bg-background px-4">
      <div className="flex items-center gap-3">
        {/* Mobile menu */}
        <Sheet>
          <SheetTrigger asChild>
            <Button variant="ghost" size="icon" className="lg:hidden">
              <Menu className="h-5 w-5" />
              <span className="sr-only">Toggle menu</span>
            </Button>
          </SheetTrigger>
          <SheetContent side="left" className="w-80 p-0">
            <ChatSidebar />
          </SheetContent>
        </Sheet>

        <div className="flex items-center gap-2">
          {company ? (
            <>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={`https://logo.clearbit.com/${company.toLowerCase()}.com`}
                alt={company}
                className="h-5 w-5 rounded object-contain"
                onError={(e) => { (e.target as HTMLImageElement).style.display = "none" }}
              />
              <h1 className="text-base font-semibold text-foreground">{company} AI Assistant</h1>
            </>
          ) : (
            <>
              <MessageSquare className="h-5 w-5 text-foreground" />
              <h1 className="text-base font-semibold text-foreground">Chat</h1>
            </>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2">
        {ragActive && (
          <Badge variant="secondary" className="gap-1 bg-success/20 text-success">
            <Database className="h-3 w-3" />
            RAG Active
          </Badge>
        )}
        {settings.streamResponse && (
          <Badge variant="secondary" className="gap-1">
            <Zap className="h-3 w-3" />
            Streaming
          </Badge>
        )}
        {isTyping && (
          <Badge variant="secondary" className="gap-1 bg-info/20 text-info">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-info opacity-75" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-info" />
            </span>
            Thinking
          </Badge>
        )}
      </div>
    </header>
  )
}
