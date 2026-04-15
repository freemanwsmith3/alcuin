export type Model =
  | "claude-opus-4-5"
  | "claude-sonnet-4-5"
  | "claude-haiku-4-5"
  | "gpt-4o"
  | "gpt-4o-mini"

export type DocumentStatus = "pending" | "processing" | "ready" | "failed"

export interface Document {
  id: string
  name: string
  status: DocumentStatus
  selected: boolean
}

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
}

export interface ChatSettings {
  model: Model
  temperature: number
  systemPrompt: string
  streamResponse: boolean
}

export interface User {
  username: string
}
