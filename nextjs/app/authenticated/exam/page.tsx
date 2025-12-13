"use client"

import React, { useState, useEffect, Suspense } from "react"
import { useSearchParams } from "next/navigation"
import { LiveKitRoom, RoomAudioRenderer, useVoiceAssistant, useLocalParticipant, useRemoteParticipants, RoomContext } from "@livekit/components-react"
import "@livekit/components-styles"
import { Room } from "livekit-client"
import { v4 as uuidv4 } from "uuid"
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
  Timer,
  Maximize2,
  Minimize2,
  MessageSquare,
  Loader2
} from "lucide-react"

interface ExamSessionResponse {
  success: boolean
  room_name: string
  token: string
  livekit_url: string
  qp_id: string
  thread_id: string
  mode: string
  message?: string
  error?: string
}

const ExamPage = () => {
  const [examStarted, setExamStarted] = useState(false)
  const [sessionInfo, setSessionInfo] = useState<ExamSessionResponse | null>(null)
  const [examMode, setExamMode] = useState<"exam" | "learn">("exam")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isMounted, setIsMounted] = useState(false)
  const searchParams = useSearchParams()

  // Create room instance with optimizations
  const [room] = useState(() => new Room({
    adaptiveStream: true,
    dynacast: true,
  }))

  // For demo purposes - in production these come from your app state
  const qpId = "qp1"
  const [threadId] = useState(() => `session_${uuidv4()}`)

  useEffect(() => {
    setIsMounted(true)

    const roomName = searchParams.get("room")
    const token = searchParams.get("token")
    const url = searchParams.get("url")
    const qpIdParam = searchParams.get("qp_id")
    const threadIdParam = searchParams.get("thread_id")

    if (roomName && token && url) {
      setSessionInfo({
        success: true,
        room_name: roomName,
        token: token,
        livekit_url: url,
        qp_id: qpIdParam || "unknown",
        thread_id: threadIdParam || "unknown",
        mode: "exam"
      })
      setExamStarted(true)
    }
  }, [searchParams])

  if (!isMounted) return null

  const startExam = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
      const response = await fetch(`${apiUrl}/start-exam-session`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          qp_id: qpId,
          thread_id: threadId,
          mode: examMode,
        }),
      })

      const data: ExamSessionResponse = await response.json()

      if (!data.success) {
        throw new Error(data.error || "Failed to start exam session")
      }

      setSessionInfo(data)
      setExamStarted(true)
    } catch (err) {
      console.error("❌ Error starting exam:", err)
      setError(err instanceof Error ? err.message : "Failed to start exam")
    } finally {
      setIsLoading(false)
    }
  }

  const endExam = () => {
    setExamStarted(false)
    setSessionInfo(null)
    room.disconnect()
  }

  return (
    <div className="relative flex h-screen w-full flex-col overflow-hidden bg-background text-foreground font-sans selection:bg-primary/20">
      {/* Background Gradient */}
      <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,var(--tw-gradient-stops))] from-primary/20 via-background to-background opacity-40"></div>

      {!examStarted ? (
        // Initial State UI
        <div className="flex-1 relative flex items-center justify-center p-4 md:p-8">
          <div className="w-full max-w-6xl h-full flex items-center justify-center gap-6">
            <motion.div layout className="relative flex items-center justify-center w-full h-full">
              <div className="relative aspect-square w-72 md:w-96">
                <Orb
                  colors={examMode === "exam" ? ["#3B82F6", "#1E40AF"] : ["#10B981", "#059669"]}
                  agentState="listening"
                  className="w-full h-full opacity-50"
                />
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-6">
                  <div className="text-center space-y-2">
                    <h1 className="text-4xl font-bold tracking-tight">VoiceExam AI</h1>
                    <p className="text-muted-foreground">
                      {examMode === "exam" ? "Strict Exam Mode" : "Interactive Learning Mode"}
                    </p>
                  </div>

                  {error && (
                    <div className="bg-destructive/10 text-destructive px-4 py-2 rounded-md text-sm">
                      {error}
                    </div>
                  )}

                  <div className="flex flex-col gap-4 items-center">
                    <div className="flex items-center gap-2 bg-background/50 p-1 rounded-full border">
                      <Button
                        variant={examMode === "exam" ? "default" : "ghost"}
                        onClick={() => setExamMode("exam")}
                        className="rounded-full"
                        size="sm"
                      >
                        Exam Mode
                      </Button>
                      <Button
                        variant={examMode === "learn" ? "default" : "ghost"}
                        onClick={() => setExamMode("learn")}
                        className="rounded-full"
                        size="sm"
                      >
                        Learn Mode
                      </Button>
                    </div>

                    <Button
                      onClick={startExam}
                      size="lg"
                      disabled={isLoading}
                      className="rounded-full px-8 shadow-lg shadow-primary/20 h-14 text-lg"
                    >
                      {isLoading ? (
                        <>
                          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                          Connecting...
                        </>
                      ) : (
                        "Start Session"
                      )}
                    </Button>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        </div>
      ) : (
        // Active Exam Room
        sessionInfo && (
          <RoomContext.Provider value={room}>
            <LiveKitRoom
              serverUrl={sessionInfo.livekit_url}
              token={sessionInfo.token}
              connect={true}
              audio={true}
              video={false}
              onDisconnected={endExam}
              className="flex-1 flex flex-col h-full"
            >
              <ExamRoomContent
                examMode={examMode}
                onEndExam={endExam}
              />
              <RoomAudioRenderer />
            </LiveKitRoom>
          </RoomContext.Provider>
        )
      )}
    </div>
  )
}

function ExamRoomContent({
  examMode,
  onEndExam,
}: {
  examMode: "exam" | "learn"
  onEndExam: () => void
}) {
  const [showContextPanel, setShowContextPanel] = useState(true)
  const { state } = useVoiceAssistant()
  const { localParticipant } = useLocalParticipant()
  const [isMuted, setIsMuted] = useState(false)
  const remoteParticipants = useRemoteParticipants()
  const [agentConnected, setAgentConnected] = useState(false)

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

  return (
    <>
      {/* Top Bar */}
      <header className="absolute top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-4">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Mic className="h-5 w-5" />
          </div>
          <span className="text-lg font-bold tracking-tight">VoiceExam AI</span>
        </div>

        <div className="flex items-center gap-2">
          <Badge variant={agentConnected ? "default" : "secondary"} className="transition-colors">
            {agentConnected ? "Agent Connected" : "Connecting..."}
          </Badge>

          <Sheet>
            <SheetTrigger asChild>
              <Button variant="ghost" size="icon" className="rounded-full">
                <Menu className="h-5 w-5" />
              </Button>
            </SheetTrigger>
            <SheetContent>
              <SheetHeader>
                <SheetTitle>Exam Controls</SheetTitle>
              </SheetHeader>
              <div className="mt-6 space-y-6">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Progress</span>
                    <span className="font-medium">0 / 10</span>
                  </div>
                  <Progress value={0} className="h-2" />
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Time Remaining</span>
                    <span className="font-medium font-mono">45:00</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Timer className="h-4 w-4" />
                    <span>Standard Time</span>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Mode</label>
                  <div className="p-2 rounded-md border bg-muted/50 text-sm">
                    {examMode === "exam" ? "Formal Exam" : "Interactive Learn"}
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
                colors={examMode === "exam" ? ["#3B82F6", "#1E40AF"] : ["#10B981", "#059669"]}
                agentState={getOrbState()}
                className="w-full h-full"
              />
            </div>
          </motion.div>

          {/* Context Panel (Text Display) */}
          <AnimatePresence mode="wait">
            {showContextPanel && (
              <motion.div
                initial={{ opacity: 0, x: 50, width: 0 }}
                animate={{ opacity: 1, x: 0, width: "50%" }}
                exit={{ opacity: 0, x: 50, width: 0 }}
                className="hidden md:block h-full max-h-[600px]"
              >
                <Card className="h-full border-border/50 bg-background/50 backdrop-blur-sm shadow-xl overflow-hidden flex flex-col">
                  <CardHeader className="border-b border-border/40 bg-muted/20">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <MessageSquare className="h-4 w-4 text-primary" />
                      Current Question
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="flex-1 overflow-y-auto p-6 space-y-6">
                    <div className="space-y-4">
                      <div className="p-4 rounded-lg bg-primary/5 border border-primary/10">
                        <h3 className="font-semibold text-lg mb-2">Question 1</h3>
                        <p className="text-muted-foreground leading-relaxed">
                          Explain the concept of &quot;Closure&quot; in JavaScript. How does it relate to variable scope and memory management? Provide a practical example of where you might use it.
                        </p>
                      </div>

                      <div className="space-y-2">
                        <h4 className="text-sm font-medium text-muted-foreground">Key Concepts to Cover:</h4>
                        <div className="flex flex-wrap gap-2">
                          <Badge variant="secondary">Lexical Scope</Badge>
                          <Badge variant="secondary">Garbage Collection</Badge>
                          <Badge variant="secondary">Data Privacy</Badge>
                        </div>
                      </div>
                    </div>
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
            onClick={onEndExam}
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
export default function ExamPageWrapper() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    }>
      <ExamPage />
    </Suspense>
  )
}
