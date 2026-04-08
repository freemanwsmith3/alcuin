"use client"

import { useEffect, useRef } from "react"
import { useChatContext } from "@/lib/chat-context"
import { cn } from "@/lib/utils"
import { User, Bot } from "lucide-react"
import ReactMarkdown from "react-markdown"
import remarkGfm from "remark-gfm"

function TypingIndicator() {
  return (
    <div className="flex items-start gap-3">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-secondary">
        <Bot className="h-4 w-4 text-foreground" />
      </div>
      <div className="flex items-center gap-1 rounded-lg bg-secondary px-4 py-3">
        <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
        <span className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground" />
      </div>
    </div>
  )
}

export function MessageList() {
  const { messages, isTyping } = useChatContext()
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isTyping])

  if (messages.length === 0 && !isTyping) {
    return (
      <div className="flex h-full flex-col items-center justify-center px-4 text-center">
        <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-xl bg-secondary">
          <Bot className="h-8 w-8 text-muted-foreground" />
        </div>
        <h2 className="mb-2 text-lg font-medium text-foreground">Start a conversation</h2>
        <p className="max-w-sm text-sm text-muted-foreground">
          Send a message to begin chatting with the AI assistant. You can also upload PDF documents for
          RAG-enhanced responses.
        </p>
      </div>
    )
  }

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto p-4">
      <div className="mx-auto flex max-w-3xl flex-col gap-6">
        {messages.map((message) => (
          <div
            key={message.id}
            className={cn("flex items-start gap-3", message.role === "user" && "flex-row-reverse")}
          >
            <div
              className={cn(
                "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
                message.role === "user" ? "bg-primary" : "bg-secondary"
              )}
            >
              {message.role === "user" ? (
                <User className="h-4 w-4 text-primary-foreground" />
              ) : (
                <Bot className="h-4 w-4 text-foreground" />
              )}
            </div>
            <div
              className={cn(
                "flex-1 rounded-lg px-4 py-3",
                message.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-foreground"
              )}
            >
              {message.role === "assistant" ? (
                <div className="prose prose-invert prose-sm max-w-none">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                      ul: ({ children }) => <ul className="mb-2 list-disc pl-4">{children}</ul>,
                      ol: ({ children }) => <ol className="mb-2 list-decimal pl-4">{children}</ol>,
                      li: ({ children }) => <li className="mb-1">{children}</li>,
                      h1: ({ children }) => (
                        <h1 className="mb-2 text-lg font-semibold">{children}</h1>
                      ),
                      h2: ({ children }) => (
                        <h2 className="mb-2 text-base font-semibold">{children}</h2>
                      ),
                      h3: ({ children }) => (
                        <h3 className="mb-2 text-sm font-semibold">{children}</h3>
                      ),
                      code: ({ className, children }) => {
                        const isInline = !className
                        return isInline ? (
                          <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">
                            {children}
                          </code>
                        ) : (
                          <code className="block overflow-x-auto rounded bg-muted p-3 font-mono text-xs">
                            {children}
                          </code>
                        )
                      },
                      pre: ({ children }) => (
                        <pre className="mb-2 overflow-x-auto rounded-md bg-muted">{children}</pre>
                      ),
                      blockquote: ({ children }) => (
                        <blockquote className="border-l-2 border-muted-foreground/30 pl-3 italic">
                          {children}
                        </blockquote>
                      ),
                      strong: ({ children }) => (
                        <strong className="font-semibold">{children}</strong>
                      ),
                      em: ({ children }) => <em className="italic">{children}</em>,
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                </div>
              ) : (
                <p className="whitespace-pre-wrap text-sm">{message.content}</p>
              )}
            </div>
          </div>
        ))}
        {isTyping && <TypingIndicator />}
      </div>
    </div>
  )
}
