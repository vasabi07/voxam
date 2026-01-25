"use client"

import { useState, useEffect } from "react"
import { toast } from "sonner"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { cn } from "@/lib/utils"
import { ChevronLeft, ChevronRight, Check, FileText, Settings2, Sparkles, GraduationCap, Clock, BookOpen } from "lucide-react"
import {
  createQuestionPaper,
  updateQuestionPaperStatus,
  createExamSession,
  getScheduledExams,
  getInProgressExams,
  getCompletedExams,
  getUserDocuments
} from "./actions"
import { useSession } from "@/lib/auth-client"

// Define types for our data
type Document = {
  id: string
  title: string
}

type Exam = {
  id: string
  title?: string
  documentId: string
  document?: { title: string }
  questionPaper?: { id: string; status: string; numQuestions: number; duration: number }
  questionPaperId?: string
  threadId?: string
  createdAt: Date
  startedAt?: Date | null
  status: string
  mode: string
}

// Wizard steps configuration
const WIZARD_STEPS = [
  { id: 1, title: "Select Document", icon: FileText },
  { id: 2, title: "Mode & Duration", icon: Settings2 },
  { id: 3, title: "Advanced", icon: Sparkles },
] as const

export default function ExamListPage() {
  const { data: session } = useSession()
  const [activeTab, setActiveTab] = useState("upcoming")
  const [open, setOpen] = useState(false)
  const [wizardStep, setWizardStep] = useState(1)
  const [isCreating, setIsCreating] = useState(false)
  const [isStarting, setIsStarting] = useState<string | null>(null) // Track which exam is starting
  const [isLoading, setIsLoading] = useState(true)

  // Real data states
  const [availableDocuments, setAvailableDocuments] = useState<Document[]>([])
  const [upcomingExams, setUpcomingExams] = useState<Exam[]>([])
  const [pastExams, setPastExams] = useState<Exam[]>([])
  const [userRegion, setUserRegion] = useState<string>("india")

  const [formData, setFormData] = useState({
    title: "",
    documentId: "",
    scheduling: "now",
    duration: "60",
    numQuestions: "10",
    difficultyLevels: ["basic", "intermediate", "advanced"] as string[],
    questionTypes: ["long_answer", "multiple_choice"] as string[],
    bloomLevels: ["remember", "understand", "apply", "analyze", "evaluate"] as string[],
    typeOfQp: "regular",
    mode: "exam" as "exam" | "learn",
  })

  // Fetch data on mount
  useEffect(() => {
    async function fetchData() {
      if (!session?.user?.id) return

      setIsLoading(true)
      try {
        // Fetch user region
        const regionResponse = await fetch("/api/user/region")
        if (regionResponse.ok) {
          const regionData = await regionResponse.json()
          setUserRegion(regionData.region || "india")
        }

        // Server actions now get userId from session automatically (IDOR fix)
        const [docsResult, scheduledResult, inProgressResult, completedResult] = await Promise.all([
          getUserDocuments(),
          getScheduledExams(),
          getInProgressExams(),
          getCompletedExams(),
        ])

        if (docsResult.success && docsResult.documents) {
          setAvailableDocuments(docsResult.documents)
        }
        // Combine scheduled + in-progress as "upcoming"
        const upcoming = [
          ...(scheduledResult.sessions || []),
          ...(inProgressResult.sessions || [])
        ]
        setUpcomingExams(upcoming)

        if (completedResult.success && completedResult.sessions) {
          setPastExams(completedResult.sessions)
        }
      } catch (error) {
        console.error('Error fetching data:', error)
      } finally {
        setIsLoading(false)
      }
    }

    fetchData()
  }, [session?.user?.id])

  const currentExams = activeTab === "upcoming" ? upcomingExams : pastExams

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target
    setFormData({ ...formData, [name]: value })
  }

  const handleSelectChange = (name: string, value: string) => {
    setFormData({ ...formData, [name]: value })
  }

  const handleMultiSelectChange = (name: string, value: string, checked: boolean) => {
    const currentValues = formData[name as keyof typeof formData] as string[]
    if (checked) {
      setFormData({ ...formData, [name]: [...currentValues, value] })
    } else {
      setFormData({ ...formData, [name]: currentValues.filter(item => item !== value) })
    }
  }

  const handleCreateExam = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!session?.user?.id) {
      toast.error('You must be logged in to create an exam')
      return
    }

    if (!formData.documentId) {
      toast.error('Please select a document')
      return
    }

    setIsCreating(true)

    try {
      // Step 1: Create QuestionPaper record in Postgres (status: PENDING)
      // Server action gets userId from session automatically (IDOR fix)
      const qpResult = await createQuestionPaper({
        documentId: formData.documentId,
        duration: parseInt(formData.duration) || 60,
        numQuestions: parseInt(formData.numQuestions) || 10,
        typeOfQp: formData.typeOfQp,
        difficulty: formData.difficultyLevels,
        bloomLevel: formData.bloomLevels,
        questionTypes: formData.questionTypes,
      })

      if (!qpResult.success || !qpResult.questionPaper) {
        throw new Error('Failed to create question paper record')
      }

      const qpId = qpResult.questionPaper.id

      // Step 2: Update status to PROCESSING
      await updateQuestionPaperStatus(qpId, 'PROCESSING')

      // Step 3: Send QP generation request to Python backend
      const accessToken = session?.session?.access_token
      if (!accessToken) {
        throw new Error('Not authenticated')
      }

      const qpResponse = await fetch('http://localhost:8000/create-qp', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({
          qp_id: qpId,
          document_id: formData.documentId,
          duration: parseInt(formData.duration) || 60,
          num_questions: parseInt(formData.numQuestions) || 10,
          difficulty_levels: formData.difficultyLevels,
          question_types: formData.questionTypes,
          bloom_levels: formData.bloomLevels,
          type_of_qp: formData.typeOfQp || 'regular',
        })
      })

      if (!qpResponse.ok) {
        await updateQuestionPaperStatus(qpId, 'FAILED')
        throw new Error('Failed to generate question paper')
      }

      // Step 4: Create ExamSession linked to QuestionPaper (status: SCHEDULED)
      // Server action gets userId from session automatically (IDOR fix)
      const threadId = `thread_${Date.now()}_${Math.random().toString(36).slice(2)}`
      const sessionResult = await createExamSession({
        documentId: formData.documentId,
        questionPaperId: qpId,
        threadId: threadId,
        mode: formData.mode === 'learn' ? 'LEARN' : 'EXAM',
      })

      if (!sessionResult.success || !sessionResult.examSession) {
        throw new Error('Failed to create exam session')
      }

      // Step 5: Start the exam immediately (calls LiveKit, spawns agent)
      const startResponse = await fetch('http://localhost:8000/start-exam-session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({
          qp_id: qpId,
          thread_id: threadId,
          mode: formData.mode,
          region: userRegion,
        })
      })

      if (!startResponse.ok) {
        throw new Error('Failed to start exam session')
      }

      const startData = await startResponse.json()

      // Close dialog and redirect to exam page
      setOpen(false)
      const params = new URLSearchParams({
        room: startData.room_name,
        token: startData.token,
        url: startData.livekit_url,
        session_id: sessionResult.examSession.id,
        qp_id: qpId,
        thread_id: threadId,
        duration: formData.duration,
        mode: formData.mode,
      })
      window.location.href = `/authenticated/exam?${params.toString()}`

    } catch (error) {
      console.error('Error creating exam:', error)
      toast.error('Failed to create exam', {
        description: error instanceof Error ? error.message : 'Unknown error'
      })
    } finally {
      setIsCreating(false)
    }
  }

  // Handler for starting an existing scheduled exam
  const handleStartExam = async (exam: Exam) => {
    if (!exam.questionPaperId || !exam.threadId) {
      toast.error('This exam is missing required data', {
        description: 'Please create a new exam.'
      })
      return
    }

    setIsStarting(exam.id)

    try {
      // Get auth token
      const accessToken = session?.session?.access_token
      if (!accessToken) {
        throw new Error('Not authenticated')
      }

      // Call the API to start the exam session
      const startResponse = await fetch('http://localhost:8000/start-exam-session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${accessToken}`
        },
        body: JSON.stringify({
          qp_id: exam.questionPaperId,
          thread_id: exam.threadId,
          mode: exam.mode.toLowerCase(),
          region: userRegion,
        })
      })

      if (!startResponse.ok) {
        throw new Error('Failed to start exam session')
      }

      const startData = await startResponse.json()

      if (startData.error) {
        throw new Error(startData.error)
      }

      // Redirect to exam page
      const params = new URLSearchParams({
        room: startData.room_name,
        token: startData.token,
        url: startData.livekit_url,
        session_id: exam.id,
        qp_id: exam.questionPaperId,
        thread_id: exam.threadId,
        duration: exam.questionPaper?.duration?.toString() || "60",
        mode: exam.mode?.toLowerCase() || "exam",
      })
      window.location.href = `/authenticated/exam?${params.toString()}`

    } catch (error) {
      console.error('Error starting exam:', error)
      toast.error('Failed to start exam', {
        description: error instanceof Error ? error.message : 'Unknown error'
      })
    } finally {
      setIsStarting(null)
    }
  }

  return (
    <>
      <div className="flex flex-wrap justify-between gap-3 p-4">
        <div className="flex min-w-72 flex-col gap-3">
          <h1 className="text-foreground text-3xl font-bold">Scheduled Exams</h1>
          <p className="text-muted-foreground text-sm">
            View and manage your upcoming and past exams.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Create New Exam Dialog */}
          <Dialog open={open} onOpenChange={(isOpen) => {
            setOpen(isOpen)
            if (isOpen) setWizardStep(1) // Reset to first step when opening
          }}>
            <DialogTrigger asChild>
              <Button className="bg-primary text-primary-foreground hover:bg-primary/90 font-bold">
                Create New Exam
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[550px] bg-background text-foreground border border-border p-0 gap-0 overflow-hidden">
              {/* Header with Step Indicator */}
              <div className="px-6 pt-6 pb-4 border-b border-border">
                <DialogHeader>
                  <DialogTitle className="text-foreground text-lg font-semibold">Create New Exam</DialogTitle>
                </DialogHeader>

                {/* Step Indicator */}
                <div className="flex items-center justify-between mt-4">
                  {WIZARD_STEPS.map((step, index) => {
                    const StepIcon = step.icon
                    const isActive = wizardStep === step.id
                    const isCompleted = wizardStep > step.id

                    return (
                      <div key={step.id} className="flex items-center flex-1">
                        <div className="flex flex-col items-center flex-1">
                          <div
                            className={cn(
                              "w-10 h-10 rounded-full flex items-center justify-center transition-all",
                              isActive && "bg-primary text-primary-foreground",
                              isCompleted && "bg-primary/20 text-primary",
                              !isActive && !isCompleted && "bg-muted text-muted-foreground"
                            )}
                          >
                            {isCompleted ? (
                              <Check className="w-5 h-5" />
                            ) : (
                              <StepIcon className="w-5 h-5" />
                            )}
                          </div>
                          <span className={cn(
                            "text-xs mt-1.5 font-medium",
                            isActive && "text-foreground",
                            !isActive && "text-muted-foreground"
                          )}>
                            {step.title}
                          </span>
                        </div>
                        {index < WIZARD_STEPS.length - 1 && (
                          <div className={cn(
                            "h-0.5 flex-1 mx-2 -mt-5 transition-colors",
                            wizardStep > step.id ? "bg-primary" : "bg-muted"
                          )} />
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Step Content */}
              <div className="px-6 py-5 min-h-[280px]">
                {/* Step 1: Select Document */}
                {wizardStep === 1 && (
                  <div className="space-y-5">
                    <div className="space-y-2">
                      <Label htmlFor="title" className="text-foreground font-medium">Exam Title (Optional)</Label>
                      <Input
                        id="title"
                        name="title"
                        type="text"
                        value={formData.title}
                        onChange={handleInputChange}
                        placeholder="e.g., Chapter 5 Review"
                        className="bg-card border-border text-foreground"
                      />
                    </div>

                    <div className="space-y-2">
                      <Label className="text-foreground font-medium">Select Document *</Label>
                      <p className="text-xs text-muted-foreground">Choose the study material for this exam</p>
                      <Select value={formData.documentId} onValueChange={(value) => handleSelectChange("documentId", value)}>
                        <SelectTrigger className="bg-card border-border text-foreground h-11">
                          <SelectValue placeholder="Choose a document" />
                        </SelectTrigger>
                        <SelectContent className="bg-card border-border">
                          {availableDocuments.length > 0 ? (
                            availableDocuments.map((doc) => (
                              <SelectItem key={doc.id} value={doc.id} className="text-foreground hover:bg-secondary">
                                <div className="flex items-center gap-2">
                                  <FileText className="w-4 h-4 text-muted-foreground" />
                                  {doc.title}
                                </div>
                              </SelectItem>
                            ))
                          ) : (
                            <div className="px-3 py-2 text-sm text-muted-foreground">
                              No documents available. Upload one first.
                            </div>
                          )}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                )}

                {/* Step 2: Mode & Duration */}
                {wizardStep === 2 && (
                  <div className="space-y-5">
                    <div className="space-y-3">
                      <Label className="text-foreground font-medium">Exam Mode</Label>
                      <div className="grid grid-cols-2 gap-3">
                        <button
                          type="button"
                          onClick={() => handleSelectChange("mode", "exam")}
                          className={cn(
                            "relative flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all",
                            formData.mode === "exam"
                              ? "border-primary bg-primary/5"
                              : "border-border hover:border-muted-foreground/50"
                          )}
                        >
                          <div className={cn(
                            "w-12 h-12 rounded-full flex items-center justify-center",
                            formData.mode === "exam" ? "bg-primary/20 text-primary" : "bg-muted text-muted-foreground"
                          )}>
                            <GraduationCap className="w-6 h-6" />
                          </div>
                          <span className="font-semibold text-foreground">Exam</span>
                          <span className="text-xs text-muted-foreground text-center">Timed, no hints, strict evaluation</span>
                          {formData.mode === "exam" && (
                            <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-primary flex items-center justify-center">
                              <Check className="w-3 h-3 text-primary-foreground" />
                            </div>
                          )}
                        </button>

                        <button
                          type="button"
                          onClick={() => handleSelectChange("mode", "learn")}
                          className={cn(
                            "relative flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all",
                            formData.mode === "learn"
                              ? "border-primary bg-primary/5"
                              : "border-border hover:border-muted-foreground/50"
                          )}
                        >
                          <div className={cn(
                            "w-12 h-12 rounded-full flex items-center justify-center",
                            formData.mode === "learn" ? "bg-primary/20 text-primary" : "bg-muted text-muted-foreground"
                          )}>
                            <BookOpen className="w-6 h-6" />
                          </div>
                          <span className="font-semibold text-foreground">Learn</span>
                          <span className="text-xs text-muted-foreground text-center">Interactive, hints allowed, Socratic</span>
                          {formData.mode === "learn" && (
                            <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-primary flex items-center justify-center">
                              <Check className="w-3 h-3 text-primary-foreground" />
                            </div>
                          )}
                        </button>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="duration" className="text-foreground font-medium flex items-center gap-2">
                          <Clock className="w-4 h-4 text-muted-foreground" />
                          Duration (mins)
                        </Label>
                        <Input
                          id="duration"
                          name="duration"
                          type="number"
                          value={formData.duration}
                          onChange={handleInputChange}
                          min="5"
                          max="180"
                          className="bg-card border-border text-foreground"
                        />
                      </div>

                      <div className="space-y-2">
                        <Label htmlFor="numQuestions" className="text-foreground font-medium">
                          Questions
                        </Label>
                        <Input
                          id="numQuestions"
                          name="numQuestions"
                          type="number"
                          value={formData.numQuestions}
                          onChange={handleInputChange}
                          min="1"
                          max="50"
                          className="bg-card border-border text-foreground"
                        />
                      </div>
                    </div>
                  </div>
                )}

                {/* Step 3: Advanced Options */}
                {wizardStep === 3 && (
                  <div className="space-y-5">
                    <div className="space-y-2">
                      <Label className="text-foreground font-medium">Question Paper Type</Label>
                      <Select value={formData.typeOfQp} onValueChange={(value) => handleSelectChange("typeOfQp", value)}>
                        <SelectTrigger className="bg-card border-border text-foreground">
                          <SelectValue placeholder="Select type" />
                        </SelectTrigger>
                        <SelectContent className="bg-card border-border">
                          <SelectItem value="regular" className="text-foreground hover:bg-secondary">Regular</SelectItem>
                          <SelectItem value="midterm" className="text-foreground hover:bg-secondary">Midterm</SelectItem>
                          <SelectItem value="final" className="text-foreground hover:bg-secondary">Final</SelectItem>
                          <SelectItem value="quiz" className="text-foreground hover:bg-secondary">Quiz</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label className="text-foreground font-medium">Difficulty Levels</Label>
                      <div className="flex flex-wrap gap-2">
                        {["basic", "intermediate", "advanced"].map((level) => (
                          <button
                            key={level}
                            type="button"
                            onClick={() => handleMultiSelectChange("difficultyLevels", level, !formData.difficultyLevels.includes(level))}
                            className={cn(
                              "px-3 py-1.5 rounded-full text-sm font-medium transition-colors",
                              formData.difficultyLevels.includes(level)
                                ? "bg-primary text-primary-foreground"
                                : "bg-muted text-muted-foreground hover:bg-muted/80"
                            )}
                          >
                            {level.charAt(0).toUpperCase() + level.slice(1)}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label className="text-foreground font-medium">Question Types</Label>
                      <div className="flex flex-wrap gap-2">
                        {[
                          { value: "multiple_choice", label: "MCQ" },
                          { value: "long_answer", label: "Long Answer" },
                          { value: "short_answer", label: "Short Answer" },
                          { value: "true_false", label: "True/False" }
                        ].map((type) => (
                          <button
                            key={type.value}
                            type="button"
                            onClick={() => handleMultiSelectChange("questionTypes", type.value, !formData.questionTypes.includes(type.value))}
                            className={cn(
                              "px-3 py-1.5 rounded-full text-sm font-medium transition-colors",
                              formData.questionTypes.includes(type.value)
                                ? "bg-primary text-primary-foreground"
                                : "bg-muted text-muted-foreground hover:bg-muted/80"
                            )}
                          >
                            {type.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-2">
                      <Label className="text-foreground font-medium">Bloom&apos;s Taxonomy</Label>
                      <div className="flex flex-wrap gap-2">
                        {[
                          { value: "remember", label: "Remember" },
                          { value: "understand", label: "Understand" },
                          { value: "apply", label: "Apply" },
                          { value: "analyze", label: "Analyze" },
                          { value: "evaluate", label: "Evaluate" },
                          { value: "create", label: "Create" }
                        ].map((level) => (
                          <button
                            key={level.value}
                            type="button"
                            onClick={() => handleMultiSelectChange("bloomLevels", level.value, !formData.bloomLevels.includes(level.value))}
                            className={cn(
                              "px-3 py-1.5 rounded-full text-sm font-medium transition-colors",
                              formData.bloomLevels.includes(level.value)
                                ? "bg-primary text-primary-foreground"
                                : "bg-muted text-muted-foreground hover:bg-muted/80"
                            )}
                          >
                            {level.label}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Footer with Navigation */}
              <div className="flex items-center justify-between px-6 py-4 border-t border-border bg-muted/30">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => wizardStep === 1 ? setOpen(false) : setWizardStep(wizardStep - 1)}
                  className="text-muted-foreground hover:text-foreground"
                  disabled={isCreating}
                >
                  {wizardStep === 1 ? (
                    "Cancel"
                  ) : (
                    <>
                      <ChevronLeft className="w-4 h-4 mr-1" />
                      Back
                    </>
                  )}
                </Button>

                {wizardStep < 3 ? (
                  <Button
                    type="button"
                    onClick={() => {
                      // Validate step 1 before proceeding
                      if (wizardStep === 1 && !formData.documentId) {
                        toast.error("Please select a document")
                        return
                      }
                      setWizardStep(wizardStep + 1)
                    }}
                    className="bg-primary text-primary-foreground hover:bg-primary/90"
                  >
                    Next
                    <ChevronRight className="w-4 h-4 ml-1" />
                  </Button>
                ) : (
                  <Button
                    type="button"
                    onClick={handleCreateExam}
                    className="bg-primary text-primary-foreground hover:bg-primary/90 font-semibold"
                    disabled={isCreating}
                  >
                    {isCreating ? "Creating..." : "Create Exam"}
                  </Button>
                )}
              </div>
            </DialogContent>
          </Dialog>

          <button className="flex items-center justify-center overflow-hidden rounded-xl h-10 bg-secondary text-foreground gap-2 text-sm font-bold px-2.5 hover:bg-secondary/80 transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" fill="currentColor" viewBox="0 0 256 256">
              <path d="M221.8,175.94C216.25,166.38,208,139.33,208,104a80,80,0,1,0-160,0c0,35.34-8.26,62.38-13.81,71.94A16,16,0,0,0,48,200H88.81a40,40,0,0,0,78.38,0H208a16,16,0,0,0,13.8-24.06ZM128,216a24,24,0,0,1-22.62-16h45.24A24,24,0,0,1,128,216ZM48,184c7.7-13.24,16-43.92,16-80a64,64,0,1,1,128,0c0,36.05,8.28,66.73,16,80Z" />
            </svg>
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="pb-3">
        <div className="flex border-b border-border px-4 gap-8">
          {["upcoming", "past"].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex flex-col items-center justify-center border-b-[3px] pb-[13px] pt-4 transition-colors ${activeTab === tab
                ? "border-b-primary text-foreground"
                : "border-b-transparent text-muted-foreground hover:text-foreground"
                }`}
            >
              <p className="text-sm font-bold">{tab === "upcoming" ? "Upcoming" : "Past"}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="px-4 py-3">
        <div className="flex overflow-hidden rounded-xl border border-border bg-background">
          <table className="flex-1">
            <thead>
              <tr className="bg-card">
                {["Exam Title", "Document", "Scheduled Date & Time", "Status"].map((header) => (
                  <th key={header} className="px-4 py-3 text-left text-foreground text-sm font-medium">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr className="border-t border-t-border">
                  <td colSpan={4} className="h-[120px] px-4 py-8 text-center">
                    <div className="flex flex-col items-center gap-3 text-muted-foreground">
                      <div className="animate-spin h-6 w-6 border-2 border-primary border-t-transparent rounded-full" />
                      <p className="text-sm">Loading exams...</p>
                    </div>
                  </td>
                </tr>
              ) : currentExams.length > 0 ? (
                currentExams.map((exam) => {
                  // Find document title
                  const document = availableDocuments.find(doc => doc.id === exam.documentId)
                  const documentTitle = exam.document?.title || document?.title || exam.documentId

                  // Format scheduled date - use startedAt if available, otherwise createdAt
                  const displayDate = exam.startedAt || exam.createdAt
                  const formattedDate = displayDate
                    ? new Date(displayDate).toLocaleString('en-US', {
                      month: 'long',
                      day: 'numeric',
                      year: 'numeric',
                      hour: 'numeric',
                      minute: '2-digit',
                      hour12: true
                    })
                    : 'Not scheduled'

                  return (
                    <tr key={exam.id} className="border-t border-t-border">
                      <td className="h-[72px] px-4 py-2 text-foreground text-sm">{exam.title}</td>
                      <td className="h-[72px] px-4 py-2 text-muted-foreground text-sm">{documentTitle}</td>
                      <td className="h-[72px] px-4 py-2 text-muted-foreground text-sm">{formattedDate}</td>
                      <td className="h-[72px] px-4 py-2 text-sm">
                        <div className="flex gap-2">
                          <button
                            onClick={() => exam.status === "SCHEDULED" ? handleStartExam(exam) : null}
                            disabled={isStarting === exam.id}
                            className={`flex items-center justify-center rounded-xl h-8 px-4 text-sm font-medium transition-colors ${exam.status === "SCHEDULED"
                              ? "bg-secondary text-foreground hover:bg-secondary/80"
                              : "bg-green-600 text-white hover:bg-green-700"
                              } ${isStarting === exam.id ? 'opacity-50 cursor-not-allowed' : ''}`}
                          >
                            {isStarting === exam.id ? "Starting..." : (exam.status === "SCHEDULED" ? "Start Exam" : "View Results")}
                          </button>
                          {exam.status === "SCHEDULED" && (
                            <button className="flex items-center justify-center rounded-xl h-8 px-3 bg-destructive text-destructive-foreground text-sm hover:bg-destructive/90">
                              Cancel
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })
              ) : (
                <tr className="border-t border-t-border">
                  <td colSpan={4} className="h-[120px] px-4 py-8 text-center">
                    <div className="flex flex-col items-center gap-3 text-muted-foreground">
                      <div className="text-lg">{activeTab === "upcoming" ? "📅" : "📊"}</div>
                      <p className="text-sm">
                        {activeTab === "upcoming" ? "No upcoming exams scheduled" : "No past exams found"}
                      </p>
                      <p className="text-xs">
                        {activeTab === "upcoming"
                          ? "Create your first exam to get started"
                          : "Completed exams will appear here"}
                      </p>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </>
  )
}
