'use client'

import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import remarkGfm from 'remark-gfm'
import rehypeKatex from 'rehype-katex'
import rehypeHighlight from 'rehype-highlight'
import 'katex/dist/katex.min.css'
import 'highlight.js/styles/github-dark.css'
import { MermaidDiagram } from './MermaidDiagram'
import { useEffect, useRef } from 'react'

// Source type for parsed sources from content
export interface ParsedSource {
  page?: number
  page_end?: number
  title?: string
  excerpt?: string
  doc_id?: string
  doc_title?: string
}

interface MarkdownContentProps {
  content: string
  className?: string
  onSourcesParsed?: (sources: ParsedSource[]) => void
}

// Regex to match the sources marker: <!-- SOURCES: [...] -->
const SOURCES_MARKER_REGEX = /<!--\s*SOURCES:\s*(\[[\s\S]*?\])\s*-->/

/**
 * Parse and extract sources from content.
 * Returns { cleanContent, sources } where sources is null if no marker found.
 */
function extractSources(text: string): { cleanContent: string; sources: ParsedSource[] | null } {
  const match = text.match(SOURCES_MARKER_REGEX)

  if (!match) {
    return { cleanContent: text, sources: null }
  }

  try {
    const sources = JSON.parse(match[1]) as ParsedSource[]
    const cleanContent = text.replace(SOURCES_MARKER_REGEX, '').trim()
    return { cleanContent, sources }
  } catch {
    // JSON parse failed, return original content
    console.warn('Failed to parse sources JSON:', match[1])
    return { cleanContent: text, sources: null }
  }
}

/**
 * Clean and normalize content for proper markdown/LaTeX rendering.
 */
function preprocessContent(text: string): string {
  let result = text

  // 1. Convert \(...\) to $...$ (inline math)
  result = result.replace(/\\\(([\s\S]+?)\\\)/g, (_, math) => `$${math}$`)

  // 2. Convert \[...\] to $$...$$ (display math)
  result = result.replace(/\\\[([\s\S]+?)\\\]/g, (_, math) => `$$${math.trim()}$$`)

  // 3. Convert standalone [ ... ] to $$...$$ when content looks like math
  result = result.replace(
    /(?<!\])\[\s*([^\[\]]*(?:\\[a-zA-Z]+|[_^]|\{|\})[^\[\]]*)\s*\](?!\()/g,
    (_, math) => `$$${math.trim()}$$`
  )

  // 4. Fix common LLM LaTeX mistakes:
  // - Remove commas/periods immediately after $$ (causes parse errors)
  result = result.replace(/\$\$([,.])/g, '$$ $1')

  // - Fix unbalanced $$ by ensuring even count (crude but helps)
  const displayMathCount = (result.match(/\$\$/g) || []).length
  if (displayMathCount % 2 !== 0) {
    // Find the last $$ and see if it's unclosed - add closing $$
    const lastIdx = result.lastIndexOf('$$')
    if (lastIdx !== -1) {
      const afterLast = result.slice(lastIdx + 2)
      // If there's substantial text after the last $$, it's probably unclosed
      if (afterLast.trim().length > 20 && !afterLast.includes('$$')) {
        // Try to find where the math should end (next sentence or paragraph)
        const endMatch = afterLast.match(/[.!?]\s|[\n\r]{2}/)
        if (endMatch && endMatch.index !== undefined) {
          const insertPos = lastIdx + 2 + endMatch.index + 1
          result = result.slice(0, insertPos) + '$$' + result.slice(insertPos)
        }
      }
    }
  }

  // 5. Strip inline source citations that the LLM writes in text
  // (These should be shown via embedded sources marker, not in text)
  result = result.replace(/\*?Source:?\*?\s*[^*\n]+(?:pages?\s*[\d\-–]+)[^*\n]*/gi, '')
  result = result.replace(/\*{2}Source:?\*{2}[^\n]+/gi, '')

  return result.trim()
}

export function MarkdownContent({ content, className, onSourcesParsed }: MarkdownContentProps) {
  // Extract sources from content first
  const { cleanContent, sources } = extractSources(content)

  // Preprocess the clean content (without sources marker)
  const processedContent = preprocessContent(cleanContent)

  // Track if we've reported sources to avoid infinite loops
  const reportedSourcesRef = useRef<string | null>(null)
  const sourcesKey = sources ? JSON.stringify(sources) : null

  // Notify parent of parsed sources (only when sources change)
  useEffect(() => {
    if (sources && sources.length > 0 && onSourcesParsed && sourcesKey !== reportedSourcesRef.current) {
      reportedSourcesRef.current = sourcesKey
      onSourcesParsed(sources)
    }
  }, [sources, onSourcesParsed, sourcesKey])

  return (
    <div className={className}>
      {/* Override KaTeX error styling to be less aggressive */}
      <style jsx global>{`
        .katex-error {
          color: inherit !important;
          background: transparent !important;
          font-family: inherit !important;
        }
      `}</style>
      <ReactMarkdown
        remarkPlugins={[remarkMath, remarkGfm]}
        rehypePlugins={[rehypeKatex, rehypeHighlight]}
        components={{
          table: ({ children }) => (
            <div className="overflow-x-auto my-4">
              <table className="min-w-full border-collapse text-sm">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-muted/50 border-b border-border">
              {children}
            </thead>
          ),
          th: ({ children }) => (
            <th className="px-3 py-2 text-left font-medium text-muted-foreground">
              {children}
            </th>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-border/50">
              {children}
            </tbody>
          ),
          tr: ({ children }) => (
            <tr className="hover:bg-muted/30 transition-colors">
              {children}
            </tr>
          ),
          td: ({ children }) => (
            <td className="px-3 py-2">
              {children}
            </td>
          ),
          code: ({ className, children, ...props }) => {
            const match = /language-(\w+)/.exec(className || '')
            const lang = match ? match[1] : ''

            // Mermaid diagrams
            if (lang === 'mermaid') {
              return <MermaidDiagram chart={String(children).trim()} />
            }

            // Inline code (no language class)
            const isInline = !className
            if (isInline) {
              return (
                <code className="px-1.5 py-0.5 rounded bg-muted text-sm font-mono" {...props}>
                  {children}
                </code>
              )
            }

            // Code blocks (handled by rehype-highlight)
            return (
              <code className={className} {...props}>
                {children}
              </code>
            )
          },
          pre: ({ children }) => (
            <pre className="overflow-x-auto rounded-lg bg-[#0d1117] p-4 my-4 text-sm">
              {children}
            </pre>
          ),
        }}
      >
        {processedContent}
      </ReactMarkdown>
    </div>
  )
}
