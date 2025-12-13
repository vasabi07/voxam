"use client"

import { AuthenticatedNavbar } from '@/components/authenticated-nav'
import { CopilotKit } from "@copilotkit/react-core"
import { useCopilotReadable } from "@copilotkit/react-core"
import "@copilotkit/react-ui/styles.css"
import { useSession } from "@/lib/auth-client"

// Separate component for CopilotKit readables (must be inside CopilotKit provider)
function CopilotUserContext() {
  const { data: session } = useSession()

  // Pass user context to the agent via CopilotKit readables
  useCopilotReadable({
    description: "The current user's information",
    value: {
      user_id: session?.user?.id || null,
      email: session?.user?.email || null,
      name: session?.user?.name || null,
    },
  })

  return null
}

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { data: session } = useSession()

  // Use user ID as thread differentiator for chat persistence
  // Each user gets their own conversation history
  const threadId = session?.user?.id ? `chat-${session.user.id}` : undefined

  return (
    <CopilotKit
      runtimeUrl="/api/copilot"
      agent="chat_agent"
      threadId={threadId}
    >
      <CopilotUserContext />
      <div className="relative flex min-h-screen w-full flex-col bg-background text-foreground">
        <AuthenticatedNavbar />
        <main className="flex-1">
          {children}
        </main>
      </div>
    </CopilotKit>
  )
}