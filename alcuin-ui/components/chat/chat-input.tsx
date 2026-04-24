"use client"

import { useState, useRef, useEffect } from "react"
import { useChatContext } from "@/lib/chat-context"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Send, Paperclip, Camera } from "lucide-react"

export function ChatInput() {
  const { sendMessage, isTyping, uploadDocument, showCamera, setShowCamera } = useChatContext()
  const [input, setInput] = useState("")
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleSubmit = async (e: { preventDefault: () => void }) => {
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

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files) {
      Array.from(files).forEach((file) => {
        if (file.type === "application/pdf") uploadDocument(file)
      })
    }
    if (fileInputRef.current) fileInputRef.current.value = ""
  }

  useEffect(() => {
    const textarea = textareaRef.current
    if (textarea) {
      textarea.style.height = "auto"
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }
  }, [input])

  return (
    <div className="border-t border-border bg-background p-4">
      <form onSubmit={handleSubmit} className="mx-auto flex max-w-3xl items-end gap-2">
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          multiple
          onChange={handleFileChange}
          className="hidden"
        />

        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={() => fileInputRef.current?.click()}
          className="h-11 w-11 shrink-0 text-muted-foreground hover:text-foreground"
          title="Attach PDF"
        >
          <Paperclip className="h-4 w-4" />
        </Button>

        <Button
          type="button"
          variant="ghost"
          size="icon"
          onClick={() => setShowCamera(!showCamera)}
          className={`h-11 w-11 shrink-0 transition-colors ${showCamera ? "text-blue-400 hover:text-blue-300" : "text-muted-foreground hover:text-foreground"}`}
          title="Toggle camera"
        >
          <Camera className="h-4 w-4" />
        </Button>

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
