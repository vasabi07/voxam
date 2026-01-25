'use client'

import { useEffect, useRef, useId } from 'react'
import mermaid from 'mermaid'

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  securityLevel: 'loose',
})

export function MermaidDiagram({ chart }: { chart: string }) {
  const ref = useRef<HTMLDivElement>(null)
  const id = useId().replace(/:/g, '-')

  useEffect(() => {
    if (ref.current) {
      mermaid.render(`mermaid-${id}`, chart).then(({ svg }) => {
        if (ref.current) {
          ref.current.innerHTML = svg
        }
      }).catch((error) => {
        console.error('Mermaid rendering error:', error)
        if (ref.current) {
          ref.current.innerHTML = `<pre class="text-red-500 text-sm">Error rendering diagram</pre>`
        }
      })
    }
  }, [chart, id])

  return <div ref={ref} className="my-4 flex justify-center" />
}
