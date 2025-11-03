import Navbar from '@/components/navbar'
import { CopilotKit } from "@copilotkit/react-core"
import "@copilotkit/react-ui/styles.css"

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <CopilotKit 
      runtimeUrl="/api/copilot"
      agent="chat_agent"
    >
      <div className="relative flex size-full min-h-screen flex-col bg-[#111b22] dark group/design-root overflow-x-hidden" style={{fontFamily: 'Inter, "Noto Sans", sans-serif'}}>
        <div className="layout-container flex h-full grow flex-col">
          <Navbar />
          <div className="flex flex-1 justify-center py-5">
            <div className="layout-content-container flex flex-col max-w-[960px] flex-1">
              {children}
            </div>
          </div>
        </div>
      </div>
    </CopilotKit>
  )
}