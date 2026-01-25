"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import {
    Trophy,
    Target,
    TrendingUp,
    TrendingDown,
    BookOpen,
    ArrowLeft,
    Loader2,
    CheckCircle2,
    XCircle,
    AlertCircle,
    Brain,
    Lightbulb,
    ChevronDown,
    ChevronUp
} from "lucide-react"
import { getExamReport } from "../../actions"
import {
    RadarChart,
    PolarGrid,
    PolarAngleAxis,
    PolarRadiusAxis,
    Radar,
    ResponsiveContainer,
    Tooltip
} from "recharts"

type BloomBreakdown = {
    remember?: number
    understand?: number
    apply?: number
    analyze?: number
    evaluate?: number
    create?: number
}

type QuestionResult = {
    question_index: number
    question_text: string
    bloom_level?: string
    difficulty?: string
    user_answer_summary?: string
    score: number
    feedback: string
    is_correct: boolean | null
    key_points_covered?: string[]
    key_points_missed?: string[]
    improvement_tips?: string
}

type Report = {
    id: string
    score: number
    grade: string
    strengths: string[]
    weaknesses: string[]
    recommendations: string[]
    summary: string
    reportJson: {
        bloom_breakdown?: BloomBreakdown
        basic_score?: number
        intermediate_score?: number
        advanced_score?: number
        question_results?: QuestionResult[]
        questions_attempted?: number
        questions_correct?: number
    } | null
    examSession: {
        document: { title: string }
        questionPaper: { numQuestions: number; duration: number }
    }
}

// Bloom's taxonomy levels with friendly labels
const BLOOM_LEVELS = [
    { key: "remember", label: "Remember", description: "Recall facts and basic concepts" },
    { key: "understand", label: "Understand", description: "Explain ideas or concepts" },
    { key: "apply", label: "Apply", description: "Use information in new situations" },
    { key: "analyze", label: "Analyze", description: "Draw connections among ideas" },
    { key: "evaluate", label: "Evaluate", description: "Justify a decision or course of action" },
    { key: "create", label: "Create", description: "Produce new or original work" },
]

function BloomTaxonomyChart({ breakdown }: { breakdown: BloomBreakdown }) {
    const data = BLOOM_LEVELS.map(level => ({
        subject: level.label,
        score: breakdown[level.key as keyof BloomBreakdown] || 0,
        fullMark: 100,
    }))

    return (
        <div className="w-full h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="70%" data={data}>
                    <PolarGrid stroke="#e5e7eb" />
                    <PolarAngleAxis
                        dataKey="subject"
                        tick={{ fill: '#6b7280', fontSize: 12 }}
                    />
                    <PolarRadiusAxis
                        angle={30}
                        domain={[0, 100]}
                        tick={{ fill: '#9ca3af', fontSize: 10 }}
                    />
                    <Radar
                        name="Score"
                        dataKey="score"
                        stroke="#0066FF"
                        fill="#0066FF"
                        fillOpacity={0.3}
                        strokeWidth={2}
                    />
                    <Tooltip
                        formatter={(value: number) => [`${Math.round(value)}%`, 'Score']}
                        contentStyle={{
                            backgroundColor: 'white',
                            border: '1px solid #e5e7eb',
                            borderRadius: '8px'
                        }}
                    />
                </RadarChart>
            </ResponsiveContainer>
        </div>
    )
}

function QuestionCard({ question, index }: { question: QuestionResult; index: number }) {
    const [expanded, setExpanded] = useState(false)
    const hasDetails = (question.key_points_covered?.length || 0) > 0 ||
                      (question.key_points_missed?.length || 0) > 0 ||
                      question.improvement_tips

    return (
        <div className="p-4 rounded-lg border bg-card">
            {/* Header */}
            <div className="flex items-start justify-between gap-4 mb-3">
                <div className="flex items-center gap-2 flex-wrap">
                    <Badge variant={question.score >= 0.7 ? "default" : question.score >= 0.4 ? "secondary" : "destructive"}>
                        Q{question.question_index + 1}
                    </Badge>
                    {question.bloom_level && (
                        <Badge variant="outline" className="capitalize text-xs">
                            {question.bloom_level}
                        </Badge>
                    )}
                    {question.difficulty && (
                        <Badge variant="outline" className="capitalize text-xs">
                            {question.difficulty}
                        </Badge>
                    )}
                    {question.is_correct === true && <CheckCircle2 className="h-4 w-4 text-green-500" />}
                    {question.is_correct === false && <XCircle className="h-4 w-4 text-red-500" />}
                </div>
                <span className="text-sm font-bold">{Math.round(question.score * 100)}%</span>
            </div>

            {/* Question Text */}
            <p className="text-sm font-medium mb-2">{question.question_text}</p>

            {/* User Answer Summary (if available) */}
            {question.user_answer_summary && (
                <div className="text-sm text-muted-foreground bg-muted/50 p-2 rounded mb-2">
                    <span className="font-medium">Your answer: </span>
                    {question.user_answer_summary}
                </div>
            )}

            {/* Feedback */}
            <p className="text-sm text-muted-foreground">{question.feedback}</p>

            {/* Expandable Details */}
            {hasDetails && (
                <>
                    <button
                        onClick={() => setExpanded(!expanded)}
                        className="flex items-center gap-1 text-sm text-primary mt-3 hover:underline"
                    >
                        {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                        {expanded ? "Hide details" : "Show details"}
                    </button>

                    {expanded && (
                        <div className="mt-3 pt-3 border-t space-y-3">
                            {/* Key Points Covered */}
                            {question.key_points_covered && question.key_points_covered.length > 0 && (
                                <div>
                                    <p className="text-xs font-medium text-green-600 mb-1 flex items-center gap-1">
                                        <CheckCircle2 className="h-3 w-3" /> Key Points Covered
                                    </p>
                                    <ul className="text-xs text-muted-foreground space-y-1 ml-4">
                                        {question.key_points_covered.map((point, i) => (
                                            <li key={i} className="list-disc">{point}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Key Points Missed */}
                            {question.key_points_missed && question.key_points_missed.length > 0 && (
                                <div>
                                    <p className="text-xs font-medium text-amber-600 mb-1 flex items-center gap-1">
                                        <XCircle className="h-3 w-3" /> Key Points Missed
                                    </p>
                                    <ul className="text-xs text-muted-foreground space-y-1 ml-4">
                                        {question.key_points_missed.map((point, i) => (
                                            <li key={i} className="list-disc">{point}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Improvement Tips */}
                            {question.improvement_tips && (
                                <div className="bg-blue-50 p-2 rounded">
                                    <p className="text-xs font-medium text-blue-600 mb-1 flex items-center gap-1">
                                        <Lightbulb className="h-3 w-3" /> How to Improve
                                    </p>
                                    <p className="text-xs text-muted-foreground">{question.improvement_tips}</p>
                                </div>
                            )}
                        </div>
                    )}
                </>
            )}
        </div>
    )
}

export default function ResultsPage() {
    const params = useParams()
    const router = useRouter()
    const sessionId = params.sessionId as string

    const [report, setReport] = useState<Report | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        async function fetchReport() {
            const result = await getExamReport(sessionId)
            if (result.success && result.report) {
                setReport(result.report as Report)
            } else {
                setError(result.error || "Failed to load report")
            }
            setLoading(false)
        }
        fetchReport()
    }, [sessionId])

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center space-y-4">
                    <Loader2 className="h-12 w-12 animate-spin mx-auto text-primary" />
                    <p className="text-muted-foreground">Loading your results...</p>
                </div>
            </div>
        )
    }

    if (error || !report) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Card className="max-w-md">
                    <CardContent className="pt-6 text-center space-y-4">
                        <AlertCircle className="h-12 w-12 mx-auto text-destructive" />
                        <p className="text-destructive">{error || "Report not found"}</p>
                        <Button onClick={() => router.push("/authenticated/examlist")}>
                            Back to Exams
                        </Button>
                    </CardContent>
                </Card>
            </div>
        )
    }

    const getGradeColor = (grade: string) => {
        if (grade.startsWith("A")) return "text-green-500"
        if (grade.startsWith("B")) return "text-blue-500"
        if (grade.startsWith("C")) return "text-yellow-500"
        if (grade.startsWith("D")) return "text-amber-500"
        return "text-red-500"
    }

    const getScoreColor = (score: number) => {
        if (score >= 80) return "bg-green-500"
        if (score >= 60) return "bg-blue-500"
        if (score >= 40) return "bg-yellow-500"
        return "bg-red-500"
    }

    const bloomBreakdown = report.reportJson?.bloom_breakdown
    const hasBloomData = bloomBreakdown && Object.values(bloomBreakdown).some(v => v > 0)

    return (
        <div className="min-h-screen bg-background p-4 md:p-8">
            <div className="max-w-4xl mx-auto space-y-6">
                {/* Header */}
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" onClick={() => router.push("/authenticated/examlist")}>
                        <ArrowLeft className="h-5 w-5" />
                    </Button>
                    <div>
                        <h1 className="text-2xl font-bold">Exam Results</h1>
                        <p className="text-muted-foreground">{report.examSession.document.title}</p>
                    </div>
                </div>

                {/* Score Card */}
                <Card className="border-2">
                    <CardContent className="pt-6">
                        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                            <div className="flex items-center gap-6">
                                <div className="relative">
                                    <Trophy className={`h-16 w-16 ${getGradeColor(report.grade)}`} />
                                </div>
                                <div>
                                    <p className="text-muted-foreground text-sm">Your Grade</p>
                                    <p className={`text-5xl font-bold ${getGradeColor(report.grade)}`}>{report.grade}</p>
                                </div>
                            </div>

                            <div className="flex-1 max-w-md w-full space-y-2">
                                <div className="flex justify-between">
                                    <span className="text-muted-foreground">Score</span>
                                    <span className="font-bold">{report.score}%</span>
                                </div>
                                <Progress value={report.score} className={`h-3 ${getScoreColor(report.score)}`} />
                                {report.reportJson?.questions_attempted !== undefined && (
                                    <p className="text-xs text-muted-foreground text-right">
                                        {report.reportJson.questions_correct || 0} / {report.reportJson.questions_attempted} questions correct
                                    </p>
                                )}
                            </div>
                        </div>
                    </CardContent>
                </Card>

                {/* Bloom's Taxonomy Chart */}
                {hasBloomData && (
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Brain className="h-5 w-5 text-primary" />
                                Bloom&apos;s Taxonomy Analysis
                            </CardTitle>
                            <CardDescription>
                                Your performance across different cognitive levels
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <BloomTaxonomyChart breakdown={bloomBreakdown!} />

                            {/* Legend with descriptions */}
                            <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mt-4">
                                {BLOOM_LEVELS.map(level => {
                                    const score = bloomBreakdown?.[level.key as keyof BloomBreakdown] || 0
                                    return (
                                        <div key={level.key} className="text-sm">
                                            <div className="flex items-center justify-between">
                                                <span className="font-medium">{level.label}</span>
                                                <span className={`font-bold ${score >= 70 ? 'text-green-500' : score >= 40 ? 'text-yellow-500' : 'text-red-500'}`}>
                                                    {Math.round(score)}%
                                                </span>
                                            </div>
                                            <p className="text-xs text-muted-foreground">{level.description}</p>
                                        </div>
                                    )
                                })}
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Summary */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Target className="h-5 w-5" />
                            Overall Feedback
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <p className="text-muted-foreground leading-relaxed">{report.summary}</p>
                    </CardContent>
                </Card>

                {/* Strengths & Weaknesses */}
                <div className="grid md:grid-cols-2 gap-4">
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2 text-green-500">
                                <TrendingUp className="h-5 w-5" />
                                Strengths
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <ul className="space-y-2">
                                {report.strengths.map((strength, idx) => (
                                    <li key={idx} className="flex items-start gap-2">
                                        <CheckCircle2 className="h-4 w-4 text-green-500 mt-1 shrink-0" />
                                        <span className="text-sm">{strength}</span>
                                    </li>
                                ))}
                            </ul>
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2 text-amber-500">
                                <TrendingDown className="h-5 w-5" />
                                Areas for Improvement
                            </CardTitle>
                        </CardHeader>
                        <CardContent>
                            <ul className="space-y-2">
                                {report.weaknesses.map((weakness, idx) => (
                                    <li key={idx} className="flex items-start gap-2">
                                        <XCircle className="h-4 w-4 text-amber-500 mt-1 shrink-0" />
                                        <span className="text-sm">{weakness}</span>
                                    </li>
                                ))}
                            </ul>
                        </CardContent>
                    </Card>
                </div>

                {/* Recommendations */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <BookOpen className="h-5 w-5" />
                            Study Recommendations
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <ul className="space-y-3">
                            {report.recommendations.map((rec, idx) => (
                                <li key={idx} className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
                                    <Badge variant="outline" className="shrink-0">{idx + 1}</Badge>
                                    <span className="text-sm">{rec}</span>
                                </li>
                            ))}
                        </ul>
                    </CardContent>
                </Card>

                {/* Question Breakdown (Enhanced) */}
                {report.reportJson?.question_results && report.reportJson.question_results.length > 0 && (
                    <Card>
                        <CardHeader>
                            <CardTitle>Question-by-Question Analysis</CardTitle>
                            <CardDescription>
                                Click on each question to see detailed feedback, key points, and improvement tips
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {report.reportJson.question_results.map((q, idx) => (
                                <QuestionCard key={idx} question={q} index={idx} />
                            ))}
                        </CardContent>
                    </Card>
                )}

                {/* Actions */}
                <div className="flex justify-center gap-4 py-6">
                    <Button variant="outline" onClick={() => router.push("/authenticated/examlist")}>
                        Back to Exams
                    </Button>
                    <Button onClick={() => router.push("/authenticated/chat")}>
                        Practice More in Chat
                    </Button>
                </div>
            </div>
        </div>
    )
}
