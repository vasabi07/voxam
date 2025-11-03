"use client"

import { useState, useEffect } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { ChevronDown } from "lucide-react"
import { createMeeting, updateMeetingQpId, getUpcomingExams, getPastExams, getUserDocuments } from "./actions"
import { useSession } from "@/lib/auth-client"

// Define types for our data
type Document = {
  id: string
  title: string
}

type Exam = {
  id: string
  title: string
  documentId: string
  scheduledAt: Date | null
  status: string
  mode: string
}

export default function ExamListPage() {
  const { data: session } = useSession()
  const [activeTab, setActiveTab] = useState("upcoming")
  const [open, setOpen] = useState(false)
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  
  // Real data states
  const [availableDocuments, setAvailableDocuments] = useState<Document[]>([])
  const [upcomingExams, setUpcomingExams] = useState<Exam[]>([])
  const [pastExams, setPastExams] = useState<Exam[]>([])
  
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
        const [docsResult, upcomingResult, pastResult] = await Promise.all([
          getUserDocuments(session.user.id),
          getUpcomingExams(session.user.id),
          getPastExams(session.user.id),
        ])

        if (docsResult.success && docsResult.documents) {
          setAvailableDocuments(docsResult.documents)
        }
        if (upcomingResult.success && upcomingResult.meetings) {
          setUpcomingExams(upcomingResult.meetings)
        }
        if (pastResult.success && pastResult.meetings) {
          setPastExams(pastResult.meetings)
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
      alert('You must be logged in to create an exam')
      return
    }
    
    setIsCreating(true)

    try {
      // Step 1: Create meeting record in Postgres using server action
      const result = await createMeeting({
        title: formData.title,
        documentId: formData.documentId,
        mode: formData.mode,
        duration: parseInt(formData.duration) || 60,
        numQuestions: parseInt(formData.numQuestions) || 10,
        typeOfQp: formData.typeOfQp,
        userId: session.user.id
      })

      if (!result.success || !result.meeting) {
        throw new Error(result.error || 'Failed to create meeting')
      }

      const meeting = result.meeting
      const qpId = meeting.id // Use meeting.id as qp_id

      // Step 2: Send QP creation request to Python backend
      const qpResponse = await fetch('http://localhost:8000/create-qp', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          qp_id: qpId,
          document_id: formData.documentId,
          duration: parseInt(formData.duration) || undefined,
          num_questions: parseInt(formData.numQuestions) || undefined,
          difficulty_levels: formData.difficultyLevels,
          question_types: formData.questionTypes,
          bloom_levels: formData.bloomLevels,
          type_of_qp: formData.typeOfQp || 'regular',
        })
      })

      if (!qpResponse.ok) {
        throw new Error('Failed to create question paper')
      }

      const qpData = await qpResponse.json()

      // Step 3: Update meeting with qpId using server action
      await updateMeetingQpId(meeting.id, qpData.qp_id)

      // Step 4: Refresh the exam list
      const upcomingResult = await getUpcomingExams(session.user.id)
      if (upcomingResult.success && upcomingResult.meetings) {
        setUpcomingExams(upcomingResult.meetings)
      }

      // Step 5: Start exam session immediately
      const sessionResponse = await fetch('http://localhost:8000/start-exam-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          qp_id: qpId,
          thread_id: meeting.threadId
        })
      })

      if (!sessionResponse.ok) {
        throw new Error('Failed to start exam session')
      }

      const sessionData = await sessionResponse.json()
      
      // Close dialog and redirect to exam page
      setOpen(false)
      window.location.href = `/authenticated/exam?room=${sessionData.room_name}&token=${sessionData.token}`

    } catch (error) {
      console.error('Error creating exam:', error)
      alert('Failed to create exam. Please try again.')
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <>
      <div className="flex flex-wrap justify-between gap-3 p-4">
        <div className="flex min-w-72 flex-col gap-3">
          <p className="text-white text-[32px] font-bold leading-tight">Scheduled Exams</p>
          <p className="text-[#93b2c8] text-sm font-normal">
            View and manage your upcoming and past exams.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Create New Exam Dialog */}
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <Button className="bg-[#47a7eb] text-[#111b22] hover:bg-[#3a96d9] font-bold">
                Create New Exam
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto bg-[#111b22] text-white border border-[#345165]">
              <DialogHeader>
                <DialogTitle className="text-white text-lg font-semibold">Create New Exam</DialogTitle>
              </DialogHeader>

              <div className="space-y-4 py-2">
                {/* Basic Info */}
                <div className="space-y-2">
                  <Label htmlFor="title" className="text-[#93b2c8]">Exam Title</Label>
                  <Input
                    id="title"
                    name="title"
                    type="text"
                    value={formData.title}
                    onChange={handleInputChange}
                    placeholder="Enter exam title"
                    className="bg-[#1a2832] border-[#345165] text-white"
                  />
                </div>

                <div className="space-y-2">
                  <Label className="text-[#93b2c8]">Select Document</Label>
                  <Select value={formData.documentId} onValueChange={(value) => handleSelectChange("documentId", value)}>
                    <SelectTrigger className="bg-[#1a2832] border-[#345165] text-white">
                      <SelectValue placeholder="Choose a document" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#1a2832] border-[#345165]">
                      {availableDocuments.map((doc) => (
                        <SelectItem key={doc.id} value={doc.id} className="text-white hover:bg-[#243847]">
                          {doc.title}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label className="text-[#93b2c8]">Exam Mode</Label>
                  <Select value={formData.mode} onValueChange={(value) => handleSelectChange("mode", value)}>
                    <SelectTrigger className="bg-[#1a2832] border-[#345165] text-white">
                      <SelectValue placeholder="Select mode" />
                    </SelectTrigger>
                    <SelectContent className="bg-[#1a2832] border-[#345165]">
                      <SelectItem value="exam" className="text-white hover:bg-[#243847]">
                        <div className="flex flex-col">
                          <span className="font-semibold">📋 Exam Mode</span>
                          <span className="text-xs text-[#93b2c8]">Formal assessment - no hints or discussions</span>
                        </div>
                      </SelectItem>
                      <SelectItem value="learn" className="text-white hover:bg-[#243847]">
                        <div className="flex flex-col">
                          <span className="font-semibold">📚 Learn Mode</span>
                          <span className="text-xs text-[#93b2c8]">Interactive learning - full guidance and feedback</span>
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                {/* Exam Configuration */}
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="duration" className="text-[#93b2c8]">Duration (minutes)</Label>
                    <Input
                      id="duration"
                      name="duration"
                      type="number"
                      value={formData.duration}
                      onChange={handleInputChange}
                      min="1"
                      className="bg-[#1a2832] border-[#345165] text-white"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="numQuestions" className="text-[#93b2c8]">Number of Questions</Label>
                    <Input
                      id="numQuestions"
                      name="numQuestions"
                      type="number"
                      value={formData.numQuestions}
                      onChange={handleInputChange}
                      min="1"
                      className="bg-[#1a2832] border-[#345165] text-white"
                    />
                  </div>
                </div>

                {/* Advanced Options - Collapsible */}
                <Collapsible open={showAdvanced} onOpenChange={setShowAdvanced} className="space-y-2">
                  <CollapsibleTrigger className="flex items-center justify-between w-full p-3 rounded-lg bg-[#1a2832] border border-[#345165] hover:bg-[#243847] transition-colors">
                    <span className="text-[#93b2c8] font-medium">Advanced Options</span>
                    <ChevronDown className={`h-4 w-4 text-[#93b2c8] transition-transform ${showAdvanced ? 'rotate-180' : ''}`} />
                  </CollapsibleTrigger>
                  
                  <CollapsibleContent className="space-y-4 pt-2">
                    <div className="space-y-2">
                      <Label className="text-[#93b2c8]">Scheduling</Label>
                      <Select value={formData.scheduling} onValueChange={(value) => handleSelectChange("scheduling", value)}>
                        <SelectTrigger className="bg-[#1a2832] border-[#345165] text-white">
                          <SelectValue placeholder="When to conduct the exam" />
                        </SelectTrigger>
                        <SelectContent className="bg-[#1a2832] border-[#345165]">
                          <SelectItem value="now" className="text-white hover:bg-[#243847]">Now</SelectItem>
                          <SelectItem value="later" className="text-white hover:bg-[#243847]">Later</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="space-y-2">
                      <Label className="text-[#93b2c8]">Question Paper Type</Label>
                      <Select value={formData.typeOfQp} onValueChange={(value) => handleSelectChange("typeOfQp", value)}>
                        <SelectTrigger className="bg-[#1a2832] border-[#345165] text-white">
                          <SelectValue placeholder="Select exam type" />
                        </SelectTrigger>
                        <SelectContent className="bg-[#1a2832] border-[#345165]">
                          <SelectItem value="regular" className="text-white hover:bg-[#243847]">Regular</SelectItem>
                          <SelectItem value="midterm" className="text-white hover:bg-[#243847]">Midterm</SelectItem>
                          <SelectItem value="final" className="text-white hover:bg-[#243847]">Final</SelectItem>
                          <SelectItem value="quiz" className="text-white hover:bg-[#243847]">Quiz</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Difficulty Levels */}
                    <div className="space-y-2">
                      <Label className="text-[#93b2c8]">Difficulty Levels</Label>
                      <div className="grid grid-cols-3 gap-2">
                        {["basic", "intermediate", "advanced"].map((level) => (
                          <div key={level} className="flex items-center space-x-2">
                            <Checkbox
                              id={`difficulty-${level}`}
                              checked={formData.difficultyLevels.includes(level)}
                              onCheckedChange={(checked) => 
                                handleMultiSelectChange("difficultyLevels", level, checked as boolean)
                              }
                              className="border-[#345165] data-[state=checked]:bg-[#47a7eb]"
                            />
                            <Label 
                              htmlFor={`difficulty-${level}`} 
                              className="text-sm text-[#93b2c8] capitalize cursor-pointer"
                            >
                              {level}
                            </Label>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Question Types */}
                    <div className="space-y-2">
                      <Label className="text-[#93b2c8]">Question Types</Label>
                      <div className="grid grid-cols-2 gap-2">
                        {[
                          { value: "multiple_choice", label: "Multiple Choice" },
                          { value: "long_answer", label: "Long Answer" },
                          { value: "short_answer", label: "Short Answer" },
                          { value: "true_false", label: "True/False" }
                        ].map((type) => (
                          <div key={type.value} className="flex items-center space-x-2">
                            <Checkbox
                              id={`type-${type.value}`}
                              checked={formData.questionTypes.includes(type.value)}
                              onCheckedChange={(checked) => 
                                handleMultiSelectChange("questionTypes", type.value, checked as boolean)
                              }
                              className="border-[#345165] data-[state=checked]:bg-[#47a7eb]"
                            />
                            <Label 
                              htmlFor={`type-${type.value}`} 
                              className="text-sm text-[#93b2c8] cursor-pointer"
                            >
                              {type.label}
                            </Label>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Bloom's Taxonomy Levels */}
                    <div className="space-y-2">
                      <Label className="text-[#93b2c8]">Bloom&apos;s Taxonomy Levels</Label>
                      <div className="grid grid-cols-2 gap-2">
                        {[
                          { value: "remember", label: "Remember" },
                          { value: "understand", label: "Understand" },
                          { value: "apply", label: "Apply" },
                          { value: "analyze", label: "Analyze" },
                          { value: "evaluate", label: "Evaluate" },
                          { value: "create", label: "Create" }
                        ].map((level) => (
                          <div key={level.value} className="flex items-center space-x-2">
                            <Checkbox
                              id={`bloom-${level.value}`}
                              checked={formData.bloomLevels.includes(level.value)}
                              onCheckedChange={(checked) => 
                                handleMultiSelectChange("bloomLevels", level.value, checked as boolean)
                              }
                              className="border-[#345165] data-[state=checked]:bg-[#47a7eb]"
                            />
                            <Label 
                              htmlFor={`bloom-${level.value}`} 
                              className="text-sm text-[#93b2c8] cursor-pointer"
                            >
                              {level.label}
                            </Label>
                          </div>
                        ))}
                      </div>
                    </div>
                  </CollapsibleContent>
                </Collapsible>
              </div>

              <div className="flex justify-end gap-2 mt-4">
                <Button 
                  variant="ghost" 
                  onClick={() => setOpen(false)} 
                  className="text-[#93b2c8] hover:text-white"
                  disabled={isCreating}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleCreateExam}
                  className="bg-[#47a7eb] text-[#111b22] hover:bg-[#3a96d9] font-semibold"
                  disabled={isCreating}
                >
                  {isCreating ? "Creating..." : "Create"}
                </Button>
              </div>
            </DialogContent>
          </Dialog>

          <button className="flex items-center justify-center overflow-hidden rounded-xl h-10 bg-[#243847] text-white gap-2 text-sm font-bold px-2.5 hover:bg-[#2a4454] transition-colors">
            <svg xmlns="http://www.w3.org/2000/svg" width="20px" height="20px" fill="currentColor" viewBox="0 0 256 256">
              <path d="M221.8,175.94C216.25,166.38,208,139.33,208,104a80,80,0,1,0-160,0c0,35.34-8.26,62.38-13.81,71.94A16,16,0,0,0,48,200H88.81a40,40,0,0,0,78.38,0H208a16,16,0,0,0,13.8-24.06ZM128,216a24,24,0,0,1-22.62-16h45.24A24,24,0,0,1,128,216ZM48,184c7.7-13.24,16-43.92,16-80a64,64,0,1,1,128,0c0,36.05,8.28,66.73,16,80Z" />
            </svg>
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="pb-3">
        <div className="flex border-b border-[#345165] px-4 gap-8">
          {["upcoming", "past"].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`flex flex-col items-center justify-center border-b-[3px] pb-[13px] pt-4 transition-colors ${
                activeTab === tab
                  ? "border-b-[#47a7eb] text-white"
                  : "border-b-transparent text-[#93b2c8] hover:text-white"
              }`}
            >
              <p className="text-sm font-bold">{tab === "upcoming" ? "Upcoming" : "Past"}</p>
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="px-4 py-3">
        <div className="flex overflow-hidden rounded-xl border border-[#345165] bg-[#111b22]">
          <table className="flex-1">
            <thead>
              <tr className="bg-[#1a2832]">
                {["Exam Title", "Document", "Scheduled Date & Time", "Status"].map((header) => (
                  <th key={header} className="px-4 py-3 text-left text-white text-sm font-medium">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr className="border-t border-t-[#345165]">
                  <td colSpan={4} className="h-[120px] px-4 py-8 text-center">
                    <div className="flex flex-col items-center gap-3 text-[#93b2c8]">
                      <div className="text-lg">⏳</div>
                      <p className="text-sm">Loading exams...</p>
                    </div>
                  </td>
                </tr>
              ) : currentExams.length > 0 ? (
                currentExams.map((exam) => {
                  // Find document title
                  const document = availableDocuments.find(doc => doc.id === exam.documentId)
                  const documentTitle = document?.title || exam.documentId
                  
                  // Format scheduled date
                  const scheduledDate = exam.scheduledAt 
                    ? new Date(exam.scheduledAt).toLocaleString('en-US', {
                        month: 'long',
                        day: 'numeric',
                        year: 'numeric',
                        hour: 'numeric',
                        minute: '2-digit',
                        hour12: true
                      })
                    : 'Not scheduled'
                  
                  return (
                    <tr key={exam.id} className="border-t border-t-[#345165]">
                      <td className="h-[72px] px-4 py-2 text-white text-sm">{exam.title}</td>
                      <td className="h-[72px] px-4 py-2 text-[#93b2c8] text-sm">{documentTitle}</td>
                      <td className="h-[72px] px-4 py-2 text-[#93b2c8] text-sm">{scheduledDate}</td>
                      <td className="h-[72px] px-4 py-2 text-sm">
                        <div className="flex gap-2">
                          <button
                            className={`flex items-center justify-center rounded-xl h-8 px-4 text-sm font-medium transition-colors ${
                              exam.status === "SCHEDULED"
                                ? "bg-[#243847] text-white hover:bg-[#2a4454]"
                                : "bg-green-600 text-white hover:bg-green-700"
                            }`}
                          >
                            {exam.status === "SCHEDULED" ? "Start Exam" : "View Results"}
                          </button>
                          {exam.status === "SCHEDULED" && (
                            <button className="flex items-center justify-center rounded-xl h-8 px-3 bg-red-600 text-white text-sm hover:bg-red-700">
                              Cancel
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })
              ) : (
                <tr className="border-t border-t-[#345165]">
                  <td colSpan={4} className="h-[120px] px-4 py-8 text-center">
                    <div className="flex flex-col items-center gap-3 text-[#93b2c8]">
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
