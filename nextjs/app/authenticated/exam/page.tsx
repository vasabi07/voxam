"use client"

import React, { useState, useEffect, Suspense } from "react"
import { useSearchParams } from "next/navigation"
import { LiveKitRoom, RoomAudioRenderer, useVoiceAssistant, useLocalParticipant, useRemoteParticipants, RoomContext, useDataChannel } from "@livekit/components-react"
import "@livekit/components-styles"
import { Room } from "livekit-client"
import { v4 as uuidv4 } from "uuid"
import { createClient } from "@/lib/supabase/client"
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
  Loader2,
  AlertTriangle,
  Clock
} from "lucide-react"
import { toast } from "sonner"

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
  const [timeRemaining, setTimeRemaining] = useState<number | null>(null) // seconds
  const [examDuration, setExamDuration] = useState<number>(60) // minutes
  const [warningsShown, setWarningsShown] = useState<Set<string>>(new Set())
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
    const durationParam = searchParams.get("duration")
    const modeParam = searchParams.get("mode")

    // Set duration and mode from URL params
    if (durationParam) {
      const mins = parseInt(durationParam)
      if (!isNaN(mins) && mins > 0) {
        setExamDuration(mins)
        setTimeRemaining(mins * 60) // Convert to seconds
      }
    }
    if (modeParam === "exam" || modeParam === "learn") {
      setExamMode(modeParam)
    }

    if (roomName && token && url) {
      setSessionInfo({
        success: true,
        room_name: roomName,
        token: token,
        livekit_url: url,
        qp_id: qpIdParam || "unknown",
        thread_id: threadIdParam || "unknown",
        mode: modeParam || "exam"
      })
      setExamStarted(true)
    }
  }, [searchParams])

  // Countdown timer effect
  useEffect(() => {
    if (!examStarted || timeRemaining === null || examMode === "learn") return

    const interval = setInterval(() => {
      setTimeRemaining(prev => {
        if (prev === null || prev <= 0) {
          clearInterval(interval)
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(interval)
  }, [examStarted, examMode, timeRemaining !== null])

  // Time-up notifications and auto-submit
  useEffect(() => {
    if (!examStarted || timeRemaining === null || examMode === "learn") return

    // 5 minute warning
    if (timeRemaining === 300 && !warningsShown.has("5min")) {
      setWarningsShown(prev => new Set(prev).add("5min"))
      toast.warning("5 minutes remaining", {
        description: "Start wrapping up your answers.",
        icon: <Clock className="h-4 w-4" />,
        duration: 5000,
      })
    }

    // 1 minute warning
    if (timeRemaining === 60 && !warningsShown.has("1min")) {
      setWarningsShown(prev => new Set(prev).add("1min"))
      toast.warning("1 minute remaining!", {
        description: "Exam will auto-submit soon.",
        icon: <AlertTriangle className="h-4 w-4" />,
        duration: 5000,
      })
    }

    // 30 second warning
    if (timeRemaining === 30 && !warningsShown.has("30sec")) {
      setWarningsShown(prev => new Set(prev).add("30sec"))
      toast.error("30 seconds remaining!", {
        description: "Your exam will be submitted automatically.",
        duration: 5000,
      })
    }

    // Time's up - auto submit
    if (timeRemaining === 0 && !warningsShown.has("timeup")) {
      setWarningsShown(prev => new Set(prev).add("timeup"))
      toast.error("Time's up!", {
        description: "Your exam has been automatically submitted.",
        duration: 8000,
      })
      // Trigger end exam - give a small delay for toast to show
      setTimeout(() => {
        endExam()
      }, 1500)
    }
  }, [timeRemaining, examStarted, examMode, warningsShown])

  // Format time as MM:SS
  const formatTime = (seconds: number | null): string => {
    if (seconds === null) return `${examDuration}:00`
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`
  }

  if (!isMounted) return null

  const startExam = async () => {
    setIsLoading(true)
    setError(null)

    try {
      // Fetch user's stored region for TTS routing
      let userRegion = "india"
      try {
        const regionResponse = await fetch("/api/user/region")
        if (regionResponse.ok) {
          const regionData = await regionResponse.json()
          userRegion = regionData.region || "india"
        }
      } catch (err) {
        console.warn("Could not fetch user region, using default:", err)
      }

      // Get auth token
      const supabase = createClient()
      const { data: { session } } = await supabase.auth.getSession()
      if (!session?.access_token) {
        throw new Error("Not authenticated")
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
      const response = await fetch(`${apiUrl}/start-exam-session`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          qp_id: qpId,
          thread_id: threadId,
          mode: examMode,
          region: userRegion,  // Pass user's stored region for TTS
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
                timeRemaining={timeRemaining}
                examDuration={examDuration}
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
  timeRemaining,
  examDuration,
}: {
  examMode: "exam" | "learn"
  onEndExam: () => void
  timeRemaining: number | null
  examDuration: number
}) {
  // Format time as MM:SS
  const formatTime = (seconds: number | null): string => {
    if (seconds === null) return `${examDuration}:00`
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`
  }
  const [showContextPanel, setShowContextPanel] = useState(true)
  const { state } = useVoiceAssistant()
  const { localParticipant } = useLocalParticipant()
  const [isMuted, setIsMuted] = useState(false)
  const remoteParticipants = useRemoteParticipants()
  const [agentConnected, setAgentConnected] = useState(false)

  // === Data Channel for receiving question data from agent ===
  const [currentQuestion, setCurrentQuestion] = useState<{
    type: string
    text: string
    options?: string[] | null
    questionNumber?: number
    totalQuestions?: number
  } | null>(null)
  const [questionProgress, setQuestionProgress] = useState<{
    current: number
    total: number
  }>({ current: 0, total: 10 })

  // Listen to data channel messages from agent
  useDataChannel((msg) => {
    try {
      const payload = JSON.parse(new TextDecoder().decode(msg.payload))
      console.log("📩 Data channel message received:", payload)

      if (payload.type === "question") {
        setCurrentQuestion({
          type: payload.type,
          text: payload.text,
          options: payload.options,
          questionNumber: payload.question_number,
          totalQuestions: payload.total_questions
        })
        // Update progress if provided
        if (payload.question_number && payload.total_questions) {
          setQuestionProgress({
            current: payload.question_number,
            total: payload.total_questions
          })
        }
      }
      // Also handle explicit progress updates
      if (payload.type === "progress") {
        setQuestionProgress({
          current: payload.current || payload.question_number || questionProgress.current,
          total: payload.total || payload.total_questions || questionProgress.total
        })
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

  // Handle manual exam end with toast
  const handleEndExam = () => {
    toast.success("Exam submitted!", {
      description: "Your answers have been recorded."
    })
    onEndExam()
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

        <div className="flex items-center gap-3">
          {/* Question Progress Indicator - Always Visible */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-background/80 backdrop-blur-sm border border-border/50">
            <span className="text-sm font-medium text-muted-foreground">Question</span>
            <span className="text-sm font-bold text-foreground">
              {questionProgress.current} / {questionProgress.total}
            </span>
          </div>

          {/* Timer Badge - Visible in Exam Mode */}
          {examMode === "exam" && timeRemaining !== null && (
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full backdrop-blur-sm border ${
              timeRemaining < 60
                ? "bg-destructive/20 border-destructive/50 text-destructive"
                : timeRemaining < 300
                  ? "bg-amber-500/20 border-amber-500/50 text-amber-500"
                  : "bg-background/80 border-border/50 text-foreground"
            }`}>
              <Timer className="h-4 w-4" />
              <span className="text-sm font-mono font-bold">{formatTime(timeRemaining)}</span>
            </div>
          )}

          <Badge variant={agentConnected ? "default" : "secondary"} className="transition-colors">
            {agentConnected ? "Connected" : "Connecting..."}
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
                    <span className="font-medium">{questionProgress.current} / {questionProgress.total}</span>
                  </div>
                  <Progress value={(questionProgress.current / questionProgress.total) * 100} className="h-2" />
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Time Remaining</span>
                    <span className={`font-medium font-mono ${timeRemaining !== null && timeRemaining < 300 ? 'text-red-500' : ''}`}>
                      {formatTime(timeRemaining)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <Timer className="h-4 w-4" />
                    <span>{examDuration} min {examMode === "learn" ? "(No limit)" : "exam"}</span>
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
                    {currentQuestion ? (
                      <div className="space-y-4">
                        <div className="p-4 rounded-lg bg-primary/5 border border-primary/10">
                          <h3 className="font-semibold text-lg mb-3">Current Question</h3>
                          <p className="text-foreground leading-relaxed whitespace-pre-wrap">
                            {currentQuestion.text}
                          </p>
                        </div>

                        {/* MCQ Options */}
                        {currentQuestion.options && currentQuestion.options.length > 0 && (
                          <div className="space-y-2">
                            <h4 className="text-sm font-medium text-muted-foreground">Options:</h4>
                            <div className="space-y-2">
                              {currentQuestion.options.map((option, idx) => (
                                <div
                                  key={idx}
                                  className="p-3 rounded-lg border border-border/50 bg-muted/20 hover:bg-muted/40 transition-colors cursor-pointer"
                                >
                                  <span className="font-medium mr-2">{String.fromCharCode(65 + idx)}.</span>
                                  {option}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="flex flex-col items-center justify-center h-full text-center text-muted-foreground">
                        <MessageSquare className="h-12 w-12 mb-4 opacity-50" />
                        <p className="text-lg font-medium">Waiting for question...</p>
                        <p className="text-sm mt-2">The AI examiner will display questions here as they are asked.</p>
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
            onClick={handleEndExam}
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
      </div >
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
