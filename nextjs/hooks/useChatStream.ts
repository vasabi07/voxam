import { useState, useCallback } from 'react'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  toolCalls?: ToolCall[]
  isFromHistory?: boolean  // Track if message is from history (for disabling UI tools)
}

export interface ToolCall {
  id: string
  name: string
  args: Record<string, unknown>
}

interface StreamEvent {
  type: 'token' | 'tool_call' | 'done' | 'error'
  content?: string
  id?: string
  name?: string
  args?: Record<string, unknown>
  message?: string
}

export function useChatStream(docId?: string) {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || isStreaming) return

    setError(null)

    // Add user message
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: content.trim()
    }
    setMessages(prev => [...prev, userMsg])

    // Create placeholder for assistant
    const assistantId = crypto.randomUUID()
    const assistantMsg: Message = {
      id: assistantId,
      role: 'assistant',
      content: '',
      toolCalls: []
    }
    setMessages(prev => [...prev, assistantMsg])

    setIsStreaming(true)

    try {
      const res = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content.trim(), doc_id: docId })
      })

      if (!res.ok) {
        const errorData = await res.json().catch(() => ({}))
        throw new Error(errorData.error || `Stream failed: ${res.status}`)
      }

      if (!res.body) {
        throw new Error('No response body')
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue

          try {
            const data: StreamEvent = JSON.parse(line.slice(6))

            if (data.type === 'token' && data.content) {
              // Append token to assistant message
              setMessages(prev => prev.map(m =>
                m.id === assistantId
                  ? { ...m, content: m.content + data.content }
                  : m
              ))
            } else if (data.type === 'tool_call' && data.name) {
              // Complete tool call received - deduplicate by ID
              const toolCall: ToolCall = {
                id: data.id || crypto.randomUUID(),
                name: data.name,
                args: typeof data.args === 'object' ? data.args as Record<string, unknown> : {}
              }
              setMessages(prev => prev.map(m => {
                if (m.id !== assistantId) return m
                // Check if tool call already exists
                const existingIds = new Set((m.toolCalls || []).map(tc => tc.id))
                if (existingIds.has(toolCall.id)) return m
                return { ...m, toolCalls: [...(m.toolCalls || []), toolCall] }
              }))
            } else if (data.type === 'error') {
              setError(data.message || 'An error occurred')
            }
          } catch (parseError) {
            console.warn('Failed to parse SSE data:', line, parseError)
          }
        }
      }

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to send message'
      setError(errorMessage)
      // Remove the empty assistant message on error
      setMessages(prev => prev.filter(m => m.id !== assistantId))
    } finally {
      setIsStreaming(false)
    }
  }, [docId, isStreaming])

  const clearMessages = useCallback(async () => {
    try {
      await fetch('/api/chat/history', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ doc_id: docId })
      })
      setMessages([])
      setError(null)
    } catch (err) {
      console.error('Failed to clear messages:', err)
    }
  }, [docId])

  const loadHistory = useCallback(async (): Promise<boolean> => {
    try {
      // Include doc_id in query params for document-specific chat history
      const url = docId
        ? `/api/chat/history?doc_id=${encodeURIComponent(docId)}`
        : '/api/chat/history'
      const res = await fetch(url)
      const data = await res.json()

      if (data.messages?.length) {
        setMessages(data.messages.map((m: {
          id: string;
          role: string;
          content: string;
          toolCalls?: ToolCall[]
        }) => ({
          id: m.id || crypto.randomUUID(),
          role: m.role as 'user' | 'assistant',
          content: m.content,
          // Preserve toolCalls from history so UI tools (upload, forms) render correctly after refresh
          toolCalls: m.toolCalls || [],
          // Mark as from history so UI tools render as disabled/read-only
          isFromHistory: true
        })))
        return true
      }
      return false
    } catch (err) {
      console.error('Failed to load history:', err)
      return false
    }
  }, [docId])

  return {
    messages,
    isStreaming,
    error,
    sendMessage,
    clearMessages,
    loadHistory
  }
}
