'use client'

import { useEffect, useRef, useState, FormEvent, useCallback } from 'react'
import { useChatStream, Message, ToolCall } from '@/hooks/useChatStream'
import { QPForm } from '@/components/copilot/QPForm'
import { IngestionUpload } from '@/components/copilot/IngestionUpload'
import { LearnPackForm } from '@/components/copilot/LearnPackForm'
import { cn } from '@/lib/utils'
import { Send, Loader2, FileText, AlertCircle } from 'lucide-react'
import { MarkdownContent, ParsedSource } from '@/components/MarkdownContent'

// Reusable sources display component
interface SourcesDisplayProps {
  sources: ParsedSource[]
  docId?: string
  onPageClick?: (page: number, targetDocId?: string) => void
}

function SourcesDisplay({ sources, docId, onPageClick }: SourcesDisplayProps) {
  if (!sources || sources.length === 0) return null

  // Debug logging for source tracking
  console.log('[Sources] Rendering sources:', sources.map(s => ({ page: s.page, doc_id: s.doc_id, title: s.doc_title })))

  // Check if sources span multiple documents
  const uniqueDocIds = new Set(sources.map(s => s.doc_id).filter(Boolean))
  const isMultiDoc = uniqueDocIds.size > 1
  const isGeneralChat = !docId

  const formatPageLabel = (source: ParsedSource, index: number) => {
    if (!source.page) return `#${index + 1}`
    if (source.page_end && source.page_end !== source.page) {
      return `p.${source.page}-${source.page_end}`
    }
    return `p.${source.page}`
  }

  const formatPageTitle = (source: ParsedSource) => {
    if (!source.page) return source.title || 'Section'
    if (source.page_end && source.page_end !== source.page) {
      return `Pages ${source.page}-${source.page_end}`
    }
    return `Page ${source.page}`
  }

  return (
    <div className="mt-3 border-t pt-3">
      <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
        <FileText className="h-3 w-3" />
        Sources ({sources.length}){isMultiDoc && ` from ${uniqueDocIds.size} documents`}
      </p>
      <div className="flex flex-wrap gap-2">
        {sources.map((source, index) => {
          const isDifferentDoc = source.doc_id && source.doc_id !== docId
          const showDocTitle = (isGeneralChat || isMultiDoc) && source.doc_title

          return (
            <button
              key={index}
              onClick={() => {
                console.log('[Sources] Clicked source:', { page: source.page, doc_id: source.doc_id, isDifferentDoc })
                if (onPageClick && source.page) {
                  // Always pass doc_id for cross-doc sources to open the correct PDF
                  onPageClick(source.page, source.doc_id || undefined)
                }
              }}
              className={cn(
                'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs transition-colors',
                source.page
                  ? 'bg-blue-50 hover:bg-blue-100 text-blue-700 cursor-pointer'
                  : 'bg-muted/50 text-muted-foreground cursor-default'
              )}
              title={`View ${source.doc_title ? source.doc_title + ' - ' : ''}${formatPageTitle(source)}`}
            >
              {showDocTitle && (
                <span className="text-muted-foreground font-normal truncate max-w-[80px]">
                  {source.doc_title}:
                </span>
              )}
              <span className="font-medium">{formatPageLabel(source, index)}</span>
              {!showDocTitle && source.title && (
                <span className="truncate max-w-[150px]">{source.title}</span>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// Tool name to Component mapping
interface ToolRendererProps {
  args: Record<string, unknown>
  docId?: string
  onPageClick?: (page: number, targetDocId?: string) => void
  isFromHistory?: boolean  // Track if this tool call is from history
}

const TOOL_RENDERERS: Record<string, React.FC<ToolRendererProps>> = {
  request_qp_form: ({ args, docId, isFromHistory }) => (
    <QPForm docId={(args.doc_id as string) || docId || 'MISSING_DOC_ID'} isFromHistory={isFromHistory} />
  ),
  request_upload_ui: ({ isFromHistory }) => <IngestionUpload isFromHistory={isFromHistory} />,
  request_learn_form: ({ args, docId, isFromHistory }) => (
    <LearnPackForm docId={(args.doc_id as string) || docId || ''} isFromHistory={isFromHistory} />
  ),
  // Legacy show_sources tool renderer - now primarily handled via embedded sources
  // Kept for backwards compatibility with older conversations
  show_sources: ({ args, onPageClick, docId }) => {
    const sources = args.sources as ParsedSource[]
    if (!sources || sources.length === 0) return null
    return <SourcesDisplay sources={sources} docId={docId} onPageClick={onPageClick} />
  },
  web_search: ({ args }) => {
    const query = args.query as string
    return (
      <div className="flex items-center gap-2 text-amber-600 text-sm py-2">
        <span className="animate-spin">&#128269;</span>
        <span>Searching the web for &quot;{query}&quot;...</span>
      </div>
    )
  }
}

interface ToolCallRendererProps {
  toolCall: ToolCall
  docId?: string
  onPageClick?: (page: number, targetDocId?: string) => void
  isFromHistory?: boolean
}

function ToolCallRenderer({ toolCall, docId, onPageClick, isFromHistory }: ToolCallRendererProps) {
  const Renderer = TOOL_RENDERERS[toolCall.name]
  if (!Renderer) return null
  return <Renderer args={toolCall.args} docId={docId} onPageClick={onPageClick} isFromHistory={isFromHistory} />
}

interface MessageBubbleProps {
  message: Message
  docId?: string
  onPageClick?: (page: number, targetDocId?: string) => void
}

function MessageBubble({ message, docId, onPageClick }: MessageBubbleProps) {
  const isUser = message.role === 'user'
  const [parsedSources, setParsedSources] = useState<ParsedSource[] | null>(null)

  // Stable callback for source parsing
  const handleSourcesParsed = useCallback((sources: ParsedSource[]) => {
    setParsedSources(sources)
  }, [])

  return (
    <div className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div
        className={cn(
          'max-w-[85%] rounded-2xl px-4 py-3',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted'
        )}
      >
        {message.content && (
          <MarkdownContent
            content={message.content}
            className="prose prose-sm max-w-none [&>p]:mb-2 [&>p:last-child]:mb-0"
            onSourcesParsed={handleSourcesParsed}
          />
        )}
        {/* Render sources parsed from content (embedded sources) */}
        {parsedSources && parsedSources.length > 0 && (
          <SourcesDisplay sources={parsedSources} docId={docId} onPageClick={onPageClick} />
        )}
        {/* Render tool calls (for UI tools like forms, and legacy show_sources) */}
        {message.toolCalls?.map((tc, i) => (
          <ToolCallRenderer key={`${tc.id}-${i}`} toolCall={tc} docId={docId} onPageClick={onPageClick} isFromHistory={message.isFromHistory} />
        ))}
      </div>
    </div>
  )
}

interface ChatProps {
  docId?: string
  documentTitle?: string
  onPageClick?: (page: number, targetDocId?: string) => void
  pendingMessage?: string | null
  onMessageSent?: () => void
  onHistoryLoaded?: (hasMessages: boolean) => void
}

export function Chat({ docId, documentTitle, onPageClick, pendingMessage, onMessageSent, onHistoryLoaded }: ChatProps) {
  const { messages, isStreaming, error, sendMessage, loadHistory } = useChatStream(docId)
  const [input, setInput] = useState('')
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Load history on mount and notify parent
  useEffect(() => {
    const load = async () => {
      const hasMessages = await loadHistory()
      onHistoryLoaded?.(hasMessages)
    }
    load()
  }, [loadHistory, onHistoryLoaded])

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  // Focus input on mount and after streaming ends
  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  // Refocus input when streaming ends
  useEffect(() => {
    if (!isStreaming) {
      inputRef.current?.focus()
    }
  }, [isStreaming])

  // Handle pending message from QuickActions
  useEffect(() => {
    if (pendingMessage && !isStreaming) {
      sendMessage(pendingMessage)
      onMessageSent?.()
    }
  }, [pendingMessage, isStreaming, sendMessage, onMessageSent])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!input.trim() || isStreaming) return
    sendMessage(input)
    setInput('')
  }

  const welcomeMessage = docId
    ? `I'm ready to help you study "${documentTitle || 'this document'}". What would you like to know?`
    : 'Welcome to the study room. What subject are we focusing on today?'

  return (
    <div className={cn(
      "flex flex-col h-full bg-background rounded-lg border overflow-hidden",
      docId && "border-l-[3px] border-l-blue-500"
    )}>
      {/* Header */}
      <div className={cn(
        "flex items-center justify-between p-3 border-b",
        docId && "bg-blue-500/5"
      )}>
        <div className="flex flex-col">
          <h2 className="font-semibold text-sm">Study Room</h2>
          {docId && documentTitle && (
            <span className="text-xs text-blue-600 truncate max-w-[200px]">
              {documentTitle}
            </span>
          )}
        </div>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
            {welcomeMessage}
          </div>
        ) : (
          messages.map(m => (
            <MessageBubble
              key={m.id}
              message={m}
              docId={docId}
              onPageClick={onPageClick}
            />
          ))
        )}

        {/* Streaming indicator */}
        {isStreaming && messages[messages.length - 1]?.content === '' && (
          <div className="flex justify-start">
            <div className="bg-muted rounded-2xl px-4 py-3">
              <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
            </div>
          </div>
        )}

        {/* Error display */}
        {error && (
          <div className="flex items-center gap-2 text-destructive text-sm p-3 bg-destructive/10 rounded-lg">
            <AlertCircle className="w-4 h-4" />
            {error}
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-3 border-t">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask anything..."
            disabled={isStreaming}
            className="flex-1 px-4 py-2 text-sm border rounded-full bg-muted/50 focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isStreaming || !input.trim()}
            className="p-2 rounded-full bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isStreaming ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
