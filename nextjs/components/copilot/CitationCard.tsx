"use client"

import { FileText, ExternalLink } from "lucide-react"

type Source = {
    page?: number
    title?: string
    excerpt?: string
}

interface CitationCardProps {
    sources: Source[]
}

export function CitationCard({ sources }: CitationCardProps) {
    if (!sources || sources.length === 0) {
        return null
    }

    return (
        <div className="mt-3 border-t pt-3">
            <p className="text-xs font-medium text-muted-foreground mb-2 flex items-center gap-1">
                <FileText className="h-3 w-3" />
                Sources ({sources.length})
            </p>
            <div className="flex flex-wrap gap-2">
                {sources.map((source, index) => (
                    <div
                        key={index}
                        className="group inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-muted/50 hover:bg-muted text-xs transition-colors cursor-default"
                        title={source.excerpt || `Page ${source.page}`}
                    >
                        <span className="font-medium text-primary">
                            {source.page ? `p.${source.page}` : `#${index + 1}`}
                        </span>
                        {source.title && (
                            <span className="text-muted-foreground truncate max-w-[150px]">
                                {source.title}
                            </span>
                        )}
                    </div>
                ))}
            </div>
            {sources.some(s => s.excerpt) && (
                <div className="mt-2 space-y-1.5">
                    {sources.filter(s => s.excerpt).slice(0, 2).map((source, index) => (
                        <div
                            key={index}
                            className="text-xs text-muted-foreground bg-muted/30 rounded p-2 border-l-2 border-primary/30"
                        >
                            <span className="font-medium text-foreground">
                                {source.page ? `Page ${source.page}` : source.title}:
                            </span>{" "}
                            <span className="italic">&quot;{source.excerpt}&quot;</span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
