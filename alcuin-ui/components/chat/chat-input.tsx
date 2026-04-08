"use client"

import { useState, useRef, useEffect } from "react"
import { useChatContext } from "@/lib/chat-context"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Send } from "lucide-react"

export function ChatInput() {
  const { sendMessage, isTyping } = useChatContext()
  const [input, setInput] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isTyping) return

    const message = input.trim()
    setInput("")
    await sendMessage(message)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = "auto"
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }
  }, [input])

  return (
    <div className="border-t border-border bg-background p-4">
      <form onSubmit={handleSubmit} className="mx-auto flex max-w-3xl gap-3">
        <Textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message..."
          className="min-h-[44px] max-h-[200px] resize-none"
          rows={1}
          disabled={isTyping}
        />
        <Button
          type="submit"
          size="icon"
          disabled={!input.trim() || isTyping}
          className="h-11 w-11 shrink-0"
        >
          <Send className="h-4 w-4" />
          <span className="sr-only">Send message</span>
        </Button>
      </form>
    </div>
  )
}
