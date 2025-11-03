"use client"
import React, {useEffect,useRef,useState} from "react"
import { Orb } from "@/components/ui/orb"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Mic, MicOff, AlertCircle } from "lucide-react"

//start creating the webrtc connection here 
const ExamPage = () => {
    const websocketRef = useRef<WebSocket | null>(null);
    const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
    const remoteAudioRef = useRef<HTMLAudioElement | null>(null);
    const [isConnected, setIsConnected] = useState(false);
    const [examMode, setExamMode] = useState<"exam" | "learn">("exam");
    const [isMuted, setIsMuted] = useState(false);
    const [examStarted, setExamStarted] = useState(false);
    
    // Helper function to add logs (console only, no UI display)
    const addLog = React.useCallback((message: string) => {
        const timestamp = new Date().toLocaleTimeString();
        const logEntry = `[${timestamp}] ${message}`;
        console.log(logEntry);
    }, []);

    const startExam = async () => {
        addLog("🚀 Starting exam and creating WebRTC connection...");
        setExamStarted(true);
        
       peerConnectionRef.current = new RTCPeerConnection({
            iceServers: [
                { urls: 'stun:stun.l.google.com:19302' }
            ]
        });
        addLog("✅ RTCPeerConnection created with STUN server");
        
        // Get user media (camera and microphone)   
        addLog("🎤 Requesting user media with Deepgram-compatible audio format...");
        
        // Configure audio constraints for Deepgram compatibility
        const audioConstraints = {
            video: false,
            audio: {
                channelCount: 1,        // Mono audio
                sampleRate: 16000,      // 16kHz sample rate (Deepgram standard)
                sampleSize: 16,         // 16-bit samples
                echoCancellation: true, // Enable echo cancellation
                noiseSuppression: true, // Enable noise suppression
                autoGainControl: true   // Enable automatic gain control
            }
        };
        
        addLog(`🔧 Audio constraints: ${JSON.stringify(audioConstraints.audio)}`);
        
        const stream = await navigator.mediaDevices.getUserMedia(audioConstraints);
        addLog("✅ User media obtained with optimized audio format");
        
        // Log the actual audio track settings
        const audioTrack = stream.getAudioTracks()[0];
        if (audioTrack) {
            const settings = audioTrack.getSettings();
            addLog(`📊 Actual audio track settings: ${JSON.stringify(settings)}`);
        }
        
        stream.getTracks().forEach(track => {
            peerConnectionRef.current?.addTrack(track, stream);
            addLog(`📡 Added ${track.kind} track to peer connection`);
        });
        
        // Create offer
        addLog("📝 Creating WebRTC offer...");
        const offer = await peerConnectionRef.current.createOffer();
        await peerConnectionRef.current.setLocalDescription(offer);
        addLog("✅ Local description set with offer");

        // Set up ICE candidate handler
        peerConnectionRef.current.onicecandidate = (event) => {
            if (event.candidate && websocketRef.current) {
                addLog(`🧊 Sending ICE candidate to server: ${event.candidate.candidate.substring(0, 50)}...`);
                websocketRef.current.send(JSON.stringify({
                    type: 'ice-candidate',
                    candidate: event.candidate
                }));
            } else if (!event.candidate) {
                addLog("🏁 ICE gathering complete (no more candidates)");
            }
        };

        // Monitor connection state
        peerConnectionRef.current.onconnectionstatechange = () => {
            const state = peerConnectionRef.current?.connectionState;
            addLog(`🔗 WebRTC connection state changed: ${state}`);
        };

        // Monitor ICE connection state
        peerConnectionRef.current.oniceconnectionstatechange = () => {
            const iceState = peerConnectionRef.current?.iceConnectionState;
            addLog(`🧊 ICE connection state: ${iceState}`);
        };

        // Monitor ICE gathering state
        peerConnectionRef.current.onicegatheringstatechange = () => {
            const gatheringState = peerConnectionRef.current?.iceGatheringState;
            addLog(`📡 ICE gathering state: ${gatheringState}`);
        };

        // Handle incoming audio tracks (TTS from server) - WebRTC native way
        peerConnectionRef.current.ontrack = (event) => {
            addLog(`🎵 Received remote ${event.track.kind} track from server`);
            
            if (event.track.kind === 'audio') {
                addLog(`📊 Audio track details: enabled=${event.track.enabled}, muted=${event.track.muted}, readyState=${event.track.readyState}`);
                
                // Reuse or create audio element for TTS playback
                if (!remoteAudioRef.current) {
                    addLog('🔧 Creating new Audio element for WebRTC stream');
                    remoteAudioRef.current = new Audio();
                    remoteAudioRef.current.autoplay = true;
                    remoteAudioRef.current.volume = 1.0;
                    
                    // Add event listeners for debugging
                    remoteAudioRef.current.onloadedmetadata = () => {
                        addLog('📊 Audio metadata loaded');
                    };
                    
                    remoteAudioRef.current.oncanplay = () => {
                        addLog('✅ Audio can play');
                    };
                    
                    remoteAudioRef.current.onplaying = () => {
                        addLog('🔊 Audio is actively playing');
                    };
                    
                    remoteAudioRef.current.onpause = () => {
                        addLog('⏸️ Audio paused');
                    };
                    
                    remoteAudioRef.current.onerror = (e) => {
                        addLog(`❌ Audio error: ${JSON.stringify(e)}`);
                        console.error('Audio element error:', e);
                    };
                    
                    remoteAudioRef.current.onstalled = () => {
                        addLog('⚠️ Audio stalled');
                    };
                    
                    remoteAudioRef.current.onwaiting = () => {
                        addLog('⏳ Audio waiting for data');
                    };
                }
                
                // Set the remote stream
                const stream = event.streams[0];
                addLog(`🌊 Setting srcObject with stream (${stream.getAudioTracks().length} audio tracks)`);
                remoteAudioRef.current.srcObject = stream;
                
                // Explicitly call play() to handle autoplay restrictions
                const playPromise = remoteAudioRef.current.play();
                if (playPromise !== undefined) {
                    playPromise
                        .then(() => {
                            addLog('✅ Audio playback started successfully');
                        })
                        .catch(err => {
                            addLog(`❌ Autoplay failed: ${err.name} - ${err.message}`);
                            addLog('💡 Tip: User interaction may be required. Try clicking the start button.');
                        });
                }
                
                // Notify server that audio track is ready
                if (websocketRef.current && websocketRef.current.readyState === WebSocket.OPEN) {
                    websocketRef.current.send(JSON.stringify({
                        type: 'track_ready',
                        message: 'Audio track is ready to receive'
                    }));
                    addLog('📤 Sent track_ready message to server');
                }
            }
        };

        // Send offer through WebSocket
        addLog("📤 Sending offer to server via WebSocket...");
        websocketRef.current?.send(JSON.stringify({
            type: 'offer',
            offer: offer,
            // Exam session details (will come from props/URL params in production)
            thread_id: 'test_thread_' + Date.now(),  // TODO: Get from exam session
            qp_id: 'qp1',  // TODO: Get from exam creation
            user_id: 'test_user_123',  // TODO: Get from auth
            mode: examMode  // Send selected mode
        }));
        addLog(`✅ Offer sent to server with exam session info (Mode: ${examMode.toUpperCase()})`);
    }

    useEffect(() => {
        // Initialize WebSocket connection
        addLog("🔌 Initializing WebSocket connection to ws://localhost:8000/ws");
        websocketRef.current = new WebSocket('ws://localhost:8000/ws');
        
        websocketRef.current.onopen = () => {
            addLog("✅ WebSocket connection opened");
            setIsConnected(true);
        };
        
        websocketRef.current.onmessage = async (event) => {
            const data = JSON.parse(event.data);
            addLog(`📨 Received WebSocket message: ${data.type}`);
            
            // Handle different message types
            if (data.type === 'answer') {
                addLog('📝 Processing WebRTC answer from server...');
                if (peerConnectionRef.current) {
                    const answer = new RTCSessionDescription(data.answer);
                    await peerConnectionRef.current.setRemoteDescription(answer);
                    addLog('✅ Answer set as remote description');
                } else {
                    addLog('❌ No peer connection available for answer');
                }
            } else if (data.type === 'ice-candidate') {
                addLog(`🧊 Processing ICE candidate from server: ${data.candidate?.candidate?.substring(0, 50)}...`);
                if (peerConnectionRef.current && data.candidate) {
                    await peerConnectionRef.current.addIceCandidate(new RTCIceCandidate(data.candidate));
                    addLog('✅ Server ICE candidate added to peer connection');
                } else {
                    addLog('❌ Cannot add ICE candidate - missing peer connection or candidate data');
                }
            } else if (data.type === 'audio_start') {
                // Agent started speaking
                addLog('🗣️ Agent started speaking');
            } else if (data.type === 'audio_complete') {
                // Agent finished speaking
                addLog('✅ Agent finished speaking');
            } else {
                // Log any other message types for debugging
                addLog(`📨 Message type: ${data.type}`);
            }
        };
        
        websocketRef.current.onerror = (error) => {
            addLog(`❌ WebSocket error: ${error}`);
        };
        
        websocketRef.current.onclose = (event) => {
            addLog(`🔌 WebSocket connection closed (code: ${event.code}, reason: ${event.reason})`);
            setIsConnected(false);
        };

        return () => {
            // Cleanup on component unmount
            addLog("🧹 Cleaning up connections...");
            websocketRef.current?.close();
            peerConnectionRef.current?.close();
            if (remoteAudioRef.current) {
                remoteAudioRef.current.srcObject = null;
            }
        };
    }, [addLog]);

    return (
        <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
            <div className="container mx-auto px-4 py-8 max-w-6xl">
                {/* Header */}
                <div className="mb-8 text-center">
                    <h1 className="text-4xl font-bold mb-2 bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                        VOXAM
                    </h1>
                    <p className="text-slate-600 dark:text-slate-400">
                        {examMode === "exam" ? "Formal Examination Mode" : "Interactive Learning Mode"}
                    </p>
                </div>

                <div className="grid lg:grid-cols-2 gap-8">
                    {/* Left Column - Voice Interface */}
                    <Card className="border-2">
                        <CardHeader>
                            <CardTitle className="flex items-center justify-between">
                                <span>Voice Assistant</span>
                                <div className="flex gap-2">
                                    {isConnected ? (
                                        <Badge variant="default" className="bg-green-500">
                                            <span className="w-2 h-2 bg-white rounded-full mr-2 animate-pulse" />
                                            Connected
                                        </Badge>
                                    ) : (
                                        <Badge variant="secondary">
                                            <AlertCircle className="w-3 h-3 mr-1" />
                                            Not Connected
                                        </Badge>
                                    )}
                                </div>
                            </CardTitle>
                            <CardDescription>
                                {!examStarted ? "Start your exam to begin voice interaction" : "Speak your answers clearly"}
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            {/* Orb Visualizer */}
                            <div className="relative w-full aspect-square max-w-md mx-auto mb-6">
                                <Orb
                                    colors={
                                        examMode === "exam" 
                                            ? ["#3B82F6", "#1E40AF"] // Blue for exam mode
                                            : ["#10B981", "#059669"] // Green for learn mode
                                    }
                                    agentState={examStarted ? "listening" : null}
                                    className="w-full h-full"
                                />
                                
                                {/* Status overlay - Minimal, no text labels */}
                                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                                    {!examStarted && (
                                        <div className="text-slate-400 text-sm">
                                            Ready to start
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Controls */}
                            <div className="flex flex-col gap-3">
                                {!examStarted ? (
                                    <>
                                        {/* Mode Selection */}
                                        <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-lg border">
                                            <label className="block text-sm font-semibold mb-2">
                                                Select Exam Mode:
                                            </label>
                                            <select 
                                                value={examMode} 
                                                onChange={(e) => setExamMode(e.target.value as "exam" | "learn")}
                                                className="w-full p-2 border border-slate-300 rounded-md bg-white dark:bg-slate-900"
                                                disabled={isConnected && examStarted}
                                            >
                                                <option value="exam">
                                                    📋 Exam Mode - Formal assessment
                                                </option>
                                                <option value="learn">
                                                    📚 Learn Mode - Interactive learning
                                                </option>
                                            </select>
                                        </div>

                                        {/* Start Button */}
                                        <Button 
                                            onClick={startExam}
                                            disabled={!isConnected}
                                            size="lg"
                                            className="w-full"
                                        >
                                            {isConnected ? "Start Exam" : "Connecting..."}
                                        </Button>
                                    </>
                                ) : (
                                    <div className="space-y-3">
                                        {/* Status Info */}
                                        <div className="p-4 rounded-lg border-2 text-center bg-slate-50 border-slate-300 dark:bg-slate-800 dark:border-slate-700">
                                            <div>
                                                <Mic className="w-6 h-6 mx-auto mb-1 text-slate-600 dark:text-slate-400" />
                                                <p className="text-sm font-semibold text-slate-700 dark:text-slate-300">
                                                    Exam in Progress
                                                </p>
                                                <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                                                    Voice conversation active
                                                </p>
                                            </div>
                                        </div>

                                        {/* Mute Button */}
                                        <Button
                                            onClick={() => setIsMuted(!isMuted)}
                                            variant="outline"
                                            className="w-full"
                                        >
                                            {isMuted ? (
                                                <>
                                                    <MicOff className="w-4 h-4 mr-2" />
                                                    Unmute Microphone
                                                </>
                                            ) : (
                                                <>
                                                    <Mic className="w-4 h-4 mr-2" />
                                                    Mute Microphone
                                                </>
                                            )}
                                        </Button>
                                    </div>
                                )}
                            </div>
                        </CardContent>
                    </Card>

                    {/* Right Column - Exam Info */}
                    <div className="space-y-6">
                        {/* Current Question Card */}
                        <Card className="border-2">
                            <CardHeader>
                                <CardTitle>Current Question</CardTitle>
                                <CardDescription>
                                    Listen carefully and answer when ready
                                </CardDescription>
                            </CardHeader>
                            <CardContent>
                                {!examStarted ? (
                                    <div className="text-center py-12 text-slate-400">
                                        <AlertCircle className="w-12 h-12 mx-auto mb-3 opacity-50" />
                                        <p>Questions will appear here once you start the exam</p>
                                    </div>
                                ) : (
                                    <div className="space-y-4">
                                        <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                                            <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">
                                                Question #1
                                            </p>
                                            <p className="text-lg font-medium">
                                                {/* Question will be populated via data channel */}
                                                Listen to the voice assistant for your question...
                                            </p>
                                        </div>

                                        <div className="text-sm text-slate-600 dark:text-slate-400">
                                            <p>💡 Tip: Speak clearly and wait for the agent to finish before responding</p>
                                        </div>
                                    </div>
                                )}
                            </CardContent>
                        </Card>

                        {/* Exam Progress */}
                        <Card>
                            <CardHeader>
                                <CardTitle className="text-base">Exam Progress</CardTitle>
                            </CardHeader>
                            <CardContent>
                                <div className="space-y-3">
                                    <div className="flex justify-between text-sm">
                                        <span className="text-slate-600">Questions Answered</span>
                                        <span className="font-semibold">0 / 10</span>
                                    </div>
                                    <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2">
                                        <div className="bg-blue-600 h-2 rounded-full" style={{width: '0%'}} />
                                    </div>
                                    <div className="flex justify-between text-sm">
                                        <span className="text-slate-600">Time Remaining</span>
                                        <span className="font-semibold">60:00</span>
                                    </div>
                                </div>
                            </CardContent>
                        </Card>

                        {/* Instructions */}
                        <Card className="border-amber-200 bg-amber-50 dark:bg-amber-900/20 dark:border-amber-800">
                            <CardHeader>
                                <CardTitle className="text-base flex items-center gap-2">
                                    <AlertCircle className="w-4 h-4" />
                                    Instructions
                                </CardTitle>
                            </CardHeader>
                            <CardContent>
                                <ul className="space-y-2 text-sm text-slate-700 dark:text-slate-300">
                                    {examMode === "exam" ? (
                                        <>
                                            <li>• Answer all questions to the best of your ability</li>
                                            <li>• No hints or help will be provided during the exam</li>
                                            <li>• Click &quot;Submit Answer&quot; when you finish each question</li>
                                            <li>• You cannot return to previous questions</li>
                                        </>
                                    ) : (
                                        <>
                                            <li>• Feel free to ask for hints or clarifications</li>
                                            <li>• The assistant will provide guidance and feedback</li>
                                            <li>• Take your time to understand each concept</li>
                                            <li>• Learning is the goal, not speed</li>
                                        </>
                                    )}
                                </ul>
                            </CardContent>
                        </Card>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default ExamPage