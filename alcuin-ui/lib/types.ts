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

export interface GraphTable {
  name: string
  columns: string[]
  rows: (string | number)[][]
}

export interface GraphRelationship {
  name: string
  from_table: string
  from_col: string
  to_table: string
  to_col: string
  pairs: [string | number, string | number][]
}

export interface GraphSchema {
  tables: GraphTable[]
  relationships: GraphRelationship[]
}

export interface GraphNode {
  id: string
  label: string
  group: string
  properties: Record<string, string>
}

export interface GraphEdge {
  source: string
  target: string
  label: string
}

export interface GraphData {
  nodes: GraphNode[]
  edges: GraphEdge[]
}
