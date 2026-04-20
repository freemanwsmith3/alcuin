"use client"

import { createContext, useContext, useState, useCallback, useEffect, useRef, type ReactNode } from "react"
import type { Message, Document, ChatSettings, User, GraphSchema, GraphData } from "./types"

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
const GATEWAY_API_KEY = process.env.NEXT_PUBLIC_GATEWAY_API_KEY ?? ""

interface ChatContextType {
  company: string | null
  user: User | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<string | null>
  register: (username: string, password: string) => Promise<string | null>
  logout: () => void
  messages: Message[]
  isTyping: boolean
  sessionId: string | null
  newSession: () => void
  sendMessage: (content: string) => Promise<void>
  documents: Document[]
  uploadDocument: (file: File) => Promise<void>
  toggleDocument: (id: string) => void
  ragActive: boolean
  settings: ChatSettings
  updateSettings: (settings: Partial<ChatSettings>) => void
  // Active tool calls
  activeTools: string[]
  // Graph
  view: "chat" | "graph"
  setView: (v: "chat" | "graph") => void
  graphSchema: GraphSchema | null
  graphData: GraphData | null
  graphLoading: boolean
  useGraph: boolean
  setUseGraph: (v: boolean) => void
  generateGraphData: (prompt: string) => Promise<string | null>
  buildGraph: () => Promise<string | null>
}

const ChatContext = createContext<ChatContextType | undefined>(undefined)

export function useChatContext() {
  const context = useContext(ChatContext)
  if (!context) throw new Error("useChatContext must be used within a ChatProvider")
  return context
}

function generateId() {
  return Math.random().toString(36).substring(2, 15)
}

// ── Token storage ─────────────────────────────────────────────────
const tokens = {
  get access()   { return typeof window !== "undefined" ? localStorage.getItem("access_token") : null },
  get refresh()  { return typeof window !== "undefined" ? localStorage.getItem("refresh_token") : null },
  get username() { return typeof window !== "undefined" ? localStorage.getItem("auth_username") : null },
  set(access: string, refresh: string, username: string) {
    localStorage.setItem("access_token",  access)
    localStorage.setItem("refresh_token", refresh)
    localStorage.setItem("auth_username", username)
  },
  clear() {
    localStorage.removeItem("access_token")
    localStorage.removeItem("refresh_token")
    localStorage.removeItem("auth_username")
  },
}

// ── Authenticated fetch with auto-refresh ─────────────────────────
async function apiFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const headers: Record<string, string> = {
    "X-API-Key": GATEWAY_API_KEY,
    ...(options.headers as Record<string, string> ?? {}),
  }
  if (tokens.access) headers["Authorization"] = `Bearer ${tokens.access}`

  let resp = await fetch(`${API_BASE}${url}`, { ...options, headers })

  if (resp.status === 401 && tokens.refresh) {
    const refreshResp = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-API-Key": GATEWAY_API_KEY },
      body: JSON.stringify({ refresh_token: tokens.refresh }),
    })
    if (refreshResp.ok) {
      const data = await refreshResp.json()
      tokens.set(data.access_token, data.refresh_token, tokens.username ?? "")
      headers["Authorization"] = `Bearer ${data.access_token}`
      resp = await fetch(`${API_BASE}${url}`, { ...options, headers })
    } else {
      tokens.clear()
    }
  }
  return resp
}

// Parses FastAPI error responses into a human-readable string.
// 422 responses have detail as an array of validation errors.
// Other errors have detail as a plain string.
function parseApiError(body: Record<string, unknown>, status: number): string {
  if (body.detail) {
    if (Array.isArray(body.detail)) {
      return body.detail.map((e: Record<string, unknown>) => String(e.msg ?? e)).join(". ")
    }
    return String(body.detail)
  }
  if (status === 409) return "That username is already taken."
  if (status === 401) return "Invalid username or password."
  if (status === 422) return "Invalid input. Check your username and password."
  return "Something went wrong. Please try again."
}

export function ChatProvider({ children, company = null }: { children: ReactNode; company?: string | null }) {
  const [user, setUser]           = useState<User | null>(null)
  const [messages, setMessages]   = useState<Message[]>([])
  const [isTyping, setIsTyping]   = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const pollTimers = useRef<Record<string, ReturnType<typeof setInterval>>>({})

  const [view, setView] = useState<"chat" | "graph">("chat")
  const [graphSchema, setGraphSchema] = useState<GraphSchema | null>(null)
  const [graphData, setGraphData] = useState<GraphData | null>(null)
  const [graphLoading, setGraphLoading] = useState(false)
  const [activeTools, setActiveTools] = useState<string[]>([])

  const [useGraph, setUseGraphState] = useState(() =>
    typeof window !== "undefined" ? localStorage.getItem("use_graph") === "true" : false
  )
  const setUseGraph = useCallback((v: boolean) => {
    setUseGraphState(v)
    if (typeof window !== "undefined") localStorage.setItem("use_graph", String(v))
  }, [])

  const [settings, setSettings] = useState<ChatSettings>({
    model: "claude-sonnet-4-5",
    temperature: 0.7,
    systemPrompt: company ? `You are a helpful AI assistant for ${company}. Answer questions helpfully and professionally.` : "",
    streamResponse: true,
  })

  const isAuthenticated = user !== null
  const ragActive = documents.some((d) => d.selected && d.status === "ready")

  // Restore session on mount
  useEffect(() => {
    if (tokens.username) {
      setUser({ username: tokens.username })
    }
  }, [])

  // ── Auth ──────────────────────────────────────────────────────────
  const login = useCallback(async (username: string, password: string): Promise<string | null> => {
    try {
      const resp = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": GATEWAY_API_KEY },
        body: JSON.stringify({ username, password }),
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        return parseApiError(err, resp.status)
      }
      const data = await resp.json()
      tokens.set(data.access_token, data.refresh_token, username)
      setUser({ username })
      return null
    } catch {
      return "Could not reach the server. Please try again."
    }
  }, [])

  const register = useCallback(async (username: string, password: string): Promise<string | null> => {
    try {
      const regResp = await fetch(`${API_BASE}/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": GATEWAY_API_KEY },
        body: JSON.stringify({ username, password }),
      })
      if (!regResp.ok) {
        const err = await regResp.json().catch(() => ({}))
        return parseApiError(err, regResp.status)
      }

      const loginResp = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": GATEWAY_API_KEY },
        body: JSON.stringify({ username, password }),
      })
      if (!loginResp.ok) return "Account created but login failed. Please sign in manually."
      const data = await loginResp.json()
      tokens.set(data.access_token, data.refresh_token, username)
      setUser({ username })
      return null
    } catch {
      return "Could not reach the server. Please try again."
    }
  }, [])

  const logout = useCallback(async () => {
    if (tokens.refresh) {
      await fetch(`${API_BASE}/api/v1/auth/logout`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-API-Key": GATEWAY_API_KEY },
        body: JSON.stringify({ refresh_token: tokens.refresh }),
      }).catch(() => {})
    }
    tokens.clear()
    setUser(null)
    setMessages([])
    setDocuments([])
    setSessionId(null)
  }, [])

  // ── Chat ──────────────────────────────────────────────────────────
  const newSession = useCallback(() => {
    setMessages([])
    setSessionId(null)
  }, [])

  const sendMessage = useCallback(async (content: string) => {
    const userMessage: Message = {
      id: generateId(),
      role: "user",
      content,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMessage])
    setIsTyping(true)

    const selectedDocIds = documents
      .filter((d) => d.selected && d.status === "ready")
      .map((d) => d.id)

    const body: Record<string, unknown> = {
      messages: [
        ...(settings.systemPrompt ? [{ role: "system", content: settings.systemPrompt }] : []),
        { role: "user", content },
      ],
      config: {
        model: settings.model,
        temperature: settings.temperature,
        max_tokens: 2048,
      },
      session_id: sessionId ?? undefined,
    }
    if (selectedDocIds.length) body.document_ids = selectedDocIds
    if (useGraph) body.use_graph = true

    try {
      if (settings.streamResponse) {
        const resp = await apiFetch("/api/v1/chat/stream", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        })

        if (!resp.ok) { setIsTyping(false); return }

        const reader = resp.body!.getReader()
        const decoder = new TextDecoder()
        let buffer = ""
        let fullText = ""
        const assistantId = generateId()

        setIsTyping(false)
        setMessages((prev) => [...prev, {
          id: assistantId, role: "assistant", content: "", timestamp: new Date(),
        }])

        let sawGraphBuild = false

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })

          let nl: number
          while ((nl = buffer.indexOf("\n\n")) !== -1) {
            const block = buffer.slice(0, nl)
            buffer = buffer.slice(nl + 2)
            for (const line of block.split("\n")) {
              if (!line.startsWith("data: ")) continue
              const raw = line.slice(6).trim()
              if (raw === "[DONE]") { setActiveTools([]); break }
              try {
                const parsed = JSON.parse(raw)
                if (parsed.session_id && !sessionId) setSessionId(parsed.session_id)
                if (parsed.text) {
                  fullText += parsed.text
                  setMessages((prev) =>
                    prev.map((m) => m.id === assistantId ? { ...m, content: fullText } : m)
                  )
                }
                if (parsed.tool_use) {
                  setActiveTools((prev) => [...prev, parsed.tool_use.name])
                  if (parsed.tool_use.name === "build_knowledge_graph") {
                    sawGraphBuild = true
                  }
                }
                if (parsed.tool_result) {
                  const { name, result } = parsed.tool_result
                  setActiveTools((prev) => prev.filter((t) => t !== name))
                  setMessages((prev) => [...prev, {
                    id: generateId(),
                    role: "tool" as const,
                    content: "",
                    timestamp: new Date(),
                    toolCall: { name, result },
                  }])
                }
              } catch { /* skip malformed */ }
            }
          }
        }
        // After stream ends, fetch fresh graph data if a build happened
        if (sawGraphBuild) {
          const gResp = await apiFetch("/api/v1/graph/")
          if (gResp.ok) {
            const gData = await gResp.json()
            if (gData.schema) setGraphSchema(gData.schema)
            if (gData.graph) setGraphData(gData.graph)
            setUseGraph(true)
            setView("graph")
          }
        }
      } else {
        const resp = await apiFetch("/api/v1/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        })
        setIsTyping(false)
        if (!resp.ok) return
        const data = await resp.json()
        if (data.session_id) setSessionId(data.session_id)
        setMessages((prev) => [...prev, {
          id: generateId(),
          role: "assistant",
          content: data.response.content,
          timestamp: new Date(),
        }])
      }
    } catch {
      setIsTyping(false)
    }
  }, [documents, settings, sessionId, useGraph])

  // ── Documents ─────────────────────────────────────────────────────
  const pollStatus = useCallback((docId: string) => {
    if (pollTimers.current[docId]) return
    const tick = async () => {
      try {
        const resp = await apiFetch(`/api/v1/rag/documents/${docId}`)
        if (!resp.ok) return
        const data = await resp.json()
        setDocuments((prev) =>
          prev.map((d) => d.id === docId
            ? { ...d, status: data.status, ...(data.status === "ready" ? { selected: true } : {}) }
            : d
          )
        )
        if (data.status === "ready" || data.status === "failed") {
          clearInterval(pollTimers.current[docId])
          delete pollTimers.current[docId]
        }
      } catch { /* keep polling */ }
    }
    tick()
    pollTimers.current[docId] = setInterval(tick, 3000)
  }, [])

  const uploadDocument = useCallback(async (file: File) => {
    const form = new FormData()
    form.append("file", file)
    try {
      const resp = await apiFetch("/api/v1/rag/documents", { method: "POST", body: form })
      if (!resp.ok) return
      const data = await resp.json()
      setDocuments((prev) => [...prev, {
        id: data.document_id, name: data.filename, status: "pending", selected: false,
      }])
      pollStatus(data.document_id)
    } catch { /* ignore */ }
  }, [pollStatus])

  const toggleDocument = useCallback((id: string) => {
    setDocuments((prev) => prev.map((d) => d.id === id ? { ...d, selected: !d.selected } : d))
  }, [])

  const updateSettings = useCallback((newSettings: Partial<ChatSettings>) => {
    setSettings((prev) => ({ ...prev, ...newSettings }))
  }, [])

  // ── Graph ─────────────────────────────────────────────────────────
  const generateGraphData = useCallback(async (prompt: string): Promise<string | null> => {
    setGraphLoading(true)
    try {
      const resp = await apiFetch("/api/v1/graph/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        return parseApiError(err, resp.status)
      }
      const data = await resp.json()
      setGraphSchema(data.schema)
      setGraphData(null)
      return null
    } catch {
      return "Could not reach the server."
    } finally {
      setGraphLoading(false)
    }
  }, [])

  const buildGraph = useCallback(async (): Promise<string | null> => {
    setGraphLoading(true)
    try {
      const resp = await apiFetch("/api/v1/graph/build", { method: "POST" })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        return parseApiError(err, resp.status)
      }
      const data = await resp.json()
      setGraphData(data.graph)
      setGraphSchema(data.schema)
      setUseGraph(true)
      return null
    } catch {
      return "Could not reach the server."
    } finally {
      setGraphLoading(false)
    }
  }, [])

  return (
    <ChatContext.Provider value={{
      company,
      user, isAuthenticated, login, register, logout,
      messages, isTyping, sessionId, newSession, sendMessage,
      documents, uploadDocument, toggleDocument, ragActive,
      settings, updateSettings,
      activeTools,
      view, setView, graphSchema, graphData, graphLoading,
      useGraph, setUseGraph, generateGraphData, buildGraph,
    }}>
      {children}
    </ChatContext.Provider>
  )
}
