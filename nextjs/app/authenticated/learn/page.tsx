"use client"

import React, { useState, useEffect, Suspense } from "react"
import { useSearchParams } from "next/navigation"
import { LiveKitRoom, RoomAudioRenderer, useVoiceAssistant, useLocalParticipant, useRemoteParticipants, RoomContext, useDataChannel } from "@livekit/components-react"
import "@livekit/components-styles"
import { Room } from "livekit-client"
import { motion, AnimatePresence } from "motion/react"
import { Orb } from "@/components/ui/orb"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet"
import { Progress } from "@/components/ui/progress"
import {
  Mic,
  MicOff,
  PhoneOff,
  Menu,
  Maximize2,
  Minimize2,
  BookOpen,
  Loader2,
  GraduationCap,
  CheckCircle2
} from "lucide-react"

interface LearnSessionResponse {
  success: boolean
  room_name: string
  token: string
  livekit_url: string
  lp_id: string
  thread_id: string
  message?: string
  error?: string
}

const LearnPage = () => {
  const [sessionStarted, setSessionStarted] = useState(false)
  const [sessionInfo, setSessionInfo] = useState<LearnSessionResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isMounted, setIsMounted] = useState(false)
  const searchParams = useSearchParams()

  // Create room instance with optimizations
  const [room] = useState(() => new Room({
    adaptiveStream: true,
    dynacast: true,
  }))

  useEffect(() => {
    setIsMounted(true)

    const roomName = searchParams.get("room")
    const token = searchParams.get("token")
    const url = searchParams.get("url")
    const lpId = searchParams.get("lp_id")
    const threadId = searchParams.get("thread_id")

    if (roomName && token && url) {
      setSessionInfo({
        success: true,
        room_name: roomName,
        token: token,
        livekit_url: url,
        lp_id: lpId || "unknown",
        thread_id: threadId || "unknown",
      })
      setSessionStarted(true)
      setIsLoading(false)
    } else {
      setError("Missing session parameters. Please start a new learning session from the chat.")
      setIsLoading(false)
    }
  }, [searchParams])

  if (!isMounted) return null

  const endSession = () => {
    setSessionStarted(false)
    setSessionInfo(null)
    room.disconnect()
    // Redirect back to chat
    window.location.href = "/authenticated/chat"
  }

  return (
    <div className="relative flex h-screen w-full flex-col overflow-hidden bg-background text-foreground font-sans selection:bg-emerald-500/20">
      {/* Background Gradient - Green theme */}
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,var(--tw-gradient-stops))] from-emerald-500/20 via-background to-background opacity-40"></div>

      {isLoading ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="flex flex-col items-center gap-4">
            <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
            <p className="text-muted-foreground">Connecting to learning session...</p>
          </div>
        </div>
      ) : error ? (
        <div className="flex-1 flex items-center justify-center p-4">
          <Card className="max-w-md">
            <CardContent className="pt-6 text-center">
              <div className="h-12 w-12 mx-auto mb-4 bg-red-100 text-red-600 rounded-full flex items-center justify-center">
                <BookOpen className="h-6 w-6" />
              </div>
              <h2 className="text-lg font-semibold mb-2">Session Not Found</h2>
              <p className="text-muted-foreground mb-4">{error}</p>
              <Button onClick={() => window.location.href = "/authenticated/chat"}>
                Go to Chat
              </Button>
            </CardContent>
          </Card>
        </div>
      ) : sessionStarted && sessionInfo ? (
        <RoomContext.Provider value={room}>
          <LiveKitRoom
            serverUrl={sessionInfo.livekit_url}
            token={sessionInfo.token}
            connect={true}
            audio={true}
            video={false}
            onDisconnected={endSession}
            className="flex-1 flex flex-col h-full"
          >
            <LearnRoomContent onEndSession={endSession} />
            <RoomAudioRenderer />
          </LiveKitRoom>
        </RoomContext.Provider>
      ) : null}
    </div>
  )
}

function LearnRoomContent({
  onEndSession,
}: {
  onEndSession: () => void
}) {
  const [showContextPanel, setShowContextPanel] = useState(true)
  const { state } = useVoiceAssistant()
  const { localParticipant } = useLocalParticipant()
  const [isMuted, setIsMuted] = useState(false)
  const remoteParticipants = useRemoteParticipants()
  const [agentConnected, setAgentConnected] = useState(false)

  // === Data Channel for receiving topic data from agent ===
  const [currentTopic, setCurrentTopic] = useState<{
    name: string
    index: number
    total: number
    key_concepts?: string[]
  } | null>(null)
  const [completedTopics, setCompletedTopics] = useState<string[]>([])

  // Listen to data channel messages from agent
  useDataChannel((msg) => {
    try {
      const payload = JSON.parse(new TextDecoder().decode(msg.payload))
      console.log("📩 Data channel message received:", payload)

      if (payload.type === "topic_change") {
        setCurrentTopic({
          name: payload.topic_name,
          index: payload.topic_index,
          total: payload.total_topics,
          key_concepts: payload.key_concepts
        })
      } else if (payload.type === "topic_completed") {
        setCompletedTopics(prev => [...prev, payload.topic_name])
      } else if (payload.type === "session_summary") {
        // Session ending - could show summary overlay
        console.log("Session summary:", payload)
      }
    } catch (e) {
      console.warn("Failed to parse data channel message:", e)
    }
  })

  useEffect(() => {
    if (remoteParticipants.length > 0) {
      setAgentConnected(true)
    } else {
      setAgentConnected(false)
    }
  }, [remoteParticipants])

  const toggleMute = async () => {
    if (localParticipant) {
      const newMutedState = !isMuted
      await localParticipant.setMicrophoneEnabled(!newMutedState)
      setIsMuted(newMutedState)
    }
  }

  // Map LiveKit state to Orb state
  const getOrbState = () => {
    if (state === "speaking") return "talking"
    return "listening"
  }

  const progressPercent = currentTopic
    ? ((currentTopic.index + 1) / currentTopic.total) * 100
    : 0

  return (
    <>
      {/* Top Bar */}
      <header className="absolute top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-600 text-white">
            <GraduationCap className="h-5 w-5" />
          </div>
          <span className="text-lg font-bold tracking-tight">Learn Mode</span>
        </div>

        <div className="flex items-center gap-2">
          <Badge
            variant={agentConnected ? "default" : "secondary"}
            className={`transition-colors ${agentConnected ? 'bg-emerald-600 hover:bg-emerald-700' : ''}`}
          >
            {agentConnected ? "Tutor Connected" : "Connecting..."}
          </Badge>

          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="rounded-full">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent>
              <SheetHeader>
                <SheetTitle>Session Info</SheetTitle>
              </SheetHeader>
              <div className="mt-6 space-y-6">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Progress</span>
                    <span className="font-medium">
                      {currentTopic ? `${currentTopic.index + 1} / ${currentTopic.total}` : "0 / 0"}
                    </span>
                  </div>
                  <Progress value={progressPercent} className="h-2 [&>div]:bg-emerald-600" />
                </div>

                {completedTopics.length > 0 && (
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Completed Topics</label>
                    <div className="space-y-1">
                      {completedTopics.map((topic, idx) => (
                        <div key={idx} className="flex items-center gap-2 text-sm text-muted-foreground">
                          <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                          <span className="truncate">{topic}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  <label className="text-sm font-medium">Mode</label>
                  <div className="p-2 rounded-md border bg-emerald-50 text-emerald-700 text-sm">
                    Interactive Learning
                  </div>
                </div>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </header>

      {/* Main Stage */}
      <main className="flex-1 relative flex items-center justify-center p-4 md:p-8">
        <div className="w-full max-w-6xl h-full flex items-center justify-center gap-6 transition-all duration-500">
          {/* Avatar / Orb Section */}
          <motion.div
            layout
            className={`relative flex items-center justify-center transition-all duration-500 ${showContextPanel ? 'w-full md:w-1/2 h-[40vh] md:h-auto' : 'w-full h-full'}`}
          >
            <div className={`relative aspect-square transition-all duration-500 ${showContextPanel ? 'w-64 md:w-80' : 'w-72 md:w-96'}`}>
              <Orb
                colors={["#10B981", "#059669"]}
                agentState={getOrbState()}
                className="w-full h-full"
              />
            </div>
          </motion.div>

          {/* Context Panel (Topic Display) */}
          <AnimatePresence mode="wait">
            {showContextPanel && (
              <motion.div
                initial={{ opacity: 0, x: 50, width: 0 }}
                animate={{ opacity: 1, x: 0, width: "50%" }}
                exit={{ opacity: 0, x: 50, width: 0 }}
                className="hidden md:block h-full max-h-[600px]"
              >
                <Card className="h-full border-border/50 bg-background/50 backdrop-blur-sm shadow-xl overflow-hidden flex flex-col">
                  <CardHeader className="border-b border-border/40 bg-emerald-50/50">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <BookOpen className="h-4 w-4 text-emerald-600" />
                      Current Topic
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex-1 overflow-y-auto p-6 space-y-6">
                    {currentTopic ? (
                      <div className="space-y-4">
                        <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-100">
                          <div className="flex items-center justify-between mb-2">
                            <Badge variant="outline" className="text-emerald-700 border-emerald-300">
                              Topic {currentTopic.index + 1} of {currentTopic.total}
                            </Badge>
                          </div>
                          <h3 className="font-semibold text-lg text-foreground">
                            {currentTopic.name}
                          </h3>
                        </div>

                        {/* Key Concepts */}
                        {currentTopic.key_concepts && currentTopic.key_concepts.length > 0 && (
                          <div className="space-y-2">
                            <h4 className="text-sm font-medium text-muted-foreground">Key Concepts:</h4>
                            <div className="flex flex-wrap gap-2">
                              {currentTopic.key_concepts.map((concept, idx) => (
                                <Badge
                                  key={idx}
                                  variant="secondary"
                                  className="bg-emerald-100 text-emerald-800 hover:bg-emerald-200"
                                >
                                  {concept}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Tips */}
                        <div className="p-3 rounded-lg bg-muted/50 text-sm text-muted-foreground">
                          <p className="font-medium mb-1">Tips:</p>
                          <ul className="list-disc list-inside space-y-1">
                            <li>Ask questions if anything is unclear</li>
                            <li>Request examples for better understanding</li>
                            <li>Say &quot;next topic&quot; when ready to move on</li>
                          </ul>
                        </div>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground">
                        <BookOpen className="h-12 w-12 mb-4 opacity-50 text-emerald-600" />
                        <p className="text-lg font-medium">Starting session...</p>
                        <p className="text-sm mt-2">Your tutor will introduce the first topic shortly.</p>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </main>

      {/* Floating Control Bar */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-50">
        <div className="flex items-center gap-4 p-2 rounded-full bg-background/80 backdrop-blur-md border border-border/40 shadow-2xl">
          <Button
            variant={isMuted ? "destructive" : "secondary"}
            size="icon"
            className="h-12 w-12 rounded-full"
            onClick={toggleMute}
          >
            {isMuted ? <MicOff className="h-5 w-5" /> : <Mic className="h-5 w-5" />}
          </Button>

          <Button
            variant="destructive"
            size="icon"
            className="h-14 w-14 rounded-full shadow-lg shadow-destructive/20"
            onClick={onEndSession}
          >
            <PhoneOff className="h-6 w-6" />
          </Button>

          <Button
            variant="outline"
            size="icon"
            className="h-12 w-12 rounded-full"
            onClick={() => setShowContextPanel(!showContextPanel)}
          >
            {showContextPanel ? <Minimize2 className="h-5 w-5" /> : <Maximize2 className="h-5 w-5" />}
          </Button>
        </div>
      </div>
    </>
  )
}

// Wrapper component with Suspense for useSearchParams
export default function LearnPageWrapper() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-emerald-600" />
      </div>
    }>
      <LearnPage />
    </Suspense>
  )
}
