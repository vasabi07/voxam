"use client"

import React, { useState, useEffect } from "react"
import { LiveKitRoom, RoomAudioRenderer, useVoiceAssistant, BarVisualizer, useLocalParticipant, RoomContext, useRemoteParticipants } from "@livekit/components-react"
import "@livekit/components-styles"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Mic, MicOff, Phone, PhoneOff, Loader2 } from "lucide-react"
import { Orb } from "@/components/ui/orb"
import { Room } from "livekit-client"
import { v4 as uuidv4 } from "uuid"

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

  // Create room instance with optimizations
  const [room] = useState(() => new Room({
    adaptiveStream: true,
    dynacast: true,
  }))

  // For demo purposes - in production these come from your app state
  const qpId = "qp1" // Replace with actual QP ID
  // Generate thread ID using UUID - stable across re-renders, no hydration issues
  const [threadId] = useState(() => `session_${uuidv4()}`)

  // Prevent hydration mismatch - only render on client side
  useEffect(() => {
    setIsMounted(true)
  }, [])

  if (!isMounted) {
    return null
  }

  const startExam = async () => {
    setIsLoading(true)
    setError(null)

    try {
      console.log("🚀 Starting exam session...")

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

      // Call your API to start the exam session
      const response = await fetch(`${apiUrl}/start-exam-session`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          // Add auth header if needed
          // "Authorization": `Bearer ${yourAuthToken}`
        },
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

      console.log("✅ Session created:", data)
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
    console.log("🛑 Ending exam session...")
    setExamStarted(false)
    setSessionInfo(null)
    room.disconnect()
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <Card className="border-purple-500/20 bg-slate-900/50 backdrop-blur">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-3xl font-bold text-white">Voice Exam System</CardTitle>
                <CardDescription className="text-slate-400">
                  Powered by LiveKit, Deepgram & Google TTS
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <Button
                  variant={examMode === "exam" ? "default" : "outline"}
                  onClick={() => !examStarted && setExamMode("exam")}
                  disabled={examStarted}
                >
                  📋 Exam Mode
                </Button>
                <Button
                  variant={examMode === "learn" ? "default" : "outline"}
                  onClick={() => !examStarted && setExamMode("learn")}
                  disabled={examStarted}
                >
                  📚 Learn Mode
                </Button>
              </div>
            </div>
          </CardHeader>
        </Card>

        {/* Main Content */}
        {!examStarted ? (
          <Card className="border-purple-500/20 bg-slate-900/50 backdrop-blur">
            <CardContent className="p-12 text-center space-y-6">
              <div className="mx-auto w-32 h-32 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                <Mic className="w-16 h-16 text-white" />
              </div>
              
              <div>
                <h2 className="text-2xl font-bold text-white mb-2">Ready to Start?</h2>
                <p className="text-slate-400">
                  {examMode === "exam"
                    ? "Strict exam mode - No hints or explanations"
                    : "Interactive learning mode - Get help and explanations"}
                </p>
              </div>

              <div className="space-y-2">
                <p className="text-sm text-slate-500">QP ID: {qpId}</p>
                <p className="text-sm text-slate-500">Thread ID: {threadId}</p>
              </div>

              {error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
                  <p className="text-red-400">{error}</p>
                </div>
              )}

              <Button
                size="lg"
                onClick={startExam}
                disabled={isLoading}
                className="bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    Connecting to Agent...
                  </>
                ) : (
                  <>
                    <Phone className="mr-2 h-5 w-5" />
                    Start Exam
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        ) : (
          sessionInfo && (
            <RoomContext.Provider value={room}>
              <LiveKitRoom
                serverUrl={sessionInfo.livekit_url}
                token={sessionInfo.token}
                connect={true}
                audio={true}
                video={false}
                onDisconnected={endExam}
                className="livekit-room"
              >
                <ExamRoom
                  examMode={examMode}
                  qpId={qpId}
                  threadId={threadId}
                  onEndExam={endExam}
                />
                <RoomAudioRenderer />
              </LiveKitRoom>
            </RoomContext.Provider>
          )
        )}
      </div>
    </div>
  )
}

// Separate component for the exam room (must be inside LiveKitRoom)
function ExamRoom({
  examMode,
  qpId,
  threadId,
  onEndExam,
}: {
  examMode: "exam" | "learn"
  qpId: string
  threadId: string
  onEndExam: () => void
}) {
  const [isMuted, setIsMuted] = useState(false)
  const [agentConnected, setAgentConnected] = useState(false)

  // Voice assistant hook provides state and controls
  const { state, audioTrack } = useVoiceAssistant()
  
  // Local participant for controlling microphone
  const { localParticipant } = useLocalParticipant()
  
  // Get remote participants to detect when agent joins
  const remoteParticipants = useRemoteParticipants()

  useEffect(() => {
    // Check if any remote participant has joined (the agent)
    if (remoteParticipants.length > 0) {
      setAgentConnected(true)
    } else {
      setAgentConnected(false)
    }
  }, [remoteParticipants])

  const toggleMute = async () => {
    if (localParticipant) {
      // When isMuted is true (currently muted), we want to unmute → setMicrophoneEnabled(true)
      // When isMuted is false (currently unmuted), we want to mute → setMicrophoneEnabled(false)
      // So we pass the OPPOSITE of isMuted
      await localParticipant.setMicrophoneEnabled(!isMuted)
      setIsMuted(!isMuted)
    }
  }

  return (
    <Card className="border-purple-500/20 bg-slate-900/50 backdrop-blur">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-white">Exam in Progress</CardTitle>
            <CardDescription className="text-slate-400">
              {examMode === "exam" ? "📋 Strict Exam Mode" : "📚 Learning Mode"}
            </CardDescription>
          </div>
          <div className="flex gap-2">
            <Badge variant={agentConnected ? "default" : "secondary"} className="gap-2">
              <div className={`w-2 h-2 rounded-full ${agentConnected ? "bg-green-500" : "bg-gray-500"}`} />
              {agentConnected ? "Agent Connected" : "Connecting..."}
            </Badge>
            <Badge variant={state === "speaking" ? "default" : "secondary"}>
              {state === "speaking" ? "🗣️ Speaking" : state === "listening" ? "👂 Listening" : "⏸️ Idle"}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Voice Visualizer */}
        <div className="flex justify-center py-8">
          {state === "speaking" ? (
            <div className="relative">
              <Orb />
              {audioTrack && (
                <div className="absolute inset-0 flex items-center justify-center">
                  <BarVisualizer
                    state={state}
                    trackRef={audioTrack}
                    barCount={5}
                    options={{ minHeight: 20 }}
                  />
                </div>
              )}
            </div>
          ) : (
            <Orb />
          )}
        </div>

        {/* Info */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="bg-slate-800/50 rounded-lg p-4">
            <p className="text-slate-400 mb-1">Question Paper</p>
            <p className="text-white font-mono">{qpId}</p>
          </div>
          <div className="bg-slate-800/50 rounded-lg p-4">
            <p className="text-slate-400 mb-1">Session ID</p>
            <p className="text-white font-mono text-xs">{threadId}</p>
          </div>
        </div>

        {/* Instructions */}
        <div className="bg-purple-500/10 border border-purple-500/20 rounded-lg p-4">
          <h3 className="text-white font-semibold mb-2">Instructions</h3>
          <ul className="text-slate-400 text-sm space-y-1">
            <li>• Speak clearly into your microphone</li>
            <li>• Wait for the agent to finish speaking before responding</li>
            {examMode === "exam" ? (
              <li>• This is a formal exam - no hints will be provided</li>
            ) : (
              <li>• Ask questions and request explanations anytime</li>
            )}
          </ul>
        </div>

        {/* Controls */}
        <div className="flex gap-4 justify-center">
          <Button
            variant={isMuted ? "destructive" : "outline"}
            onClick={toggleMute}
            className="gap-2"
          >
            {isMuted ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            {isMuted ? "Unmute" : "Mute"}
          </Button>

          <Button
            variant="destructive"
            onClick={onEndExam}
            className="gap-2"
          >
            <PhoneOff className="w-4 h-4" />
            End Exam
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

export default ExamPage
