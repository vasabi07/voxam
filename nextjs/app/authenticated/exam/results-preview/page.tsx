"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import {
    Trophy,
    Target,
    TrendingUp,
    TrendingDown,
    BookOpen,
    ArrowLeft,
    CheckCircle2,
    XCircle,
    Brain,
    Lightbulb,
    ChevronDown,
    ChevronUp
} from "lucide-react"
import {
    RadarChart,
    PolarGrid,
    PolarAngleAxis,
    PolarRadiusAxis,
    Radar,
    ResponsiveContainer,
    Tooltip
} from "recharts"
import { useRouter } from "next/navigation"

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

// Mock data for preview
const MOCK_REPORT = {
    id: "preview-report",
    score: 73,
    grade: "B+",
    strengths: [
        "Strong understanding of core photosynthesis concepts",
        "Excellent recall of chemical formulas and equations",
        "Good ability to explain cellular respiration steps",
        "Clear articulation of the relationship between light and dark reactions"
    ],
    weaknesses: [
        "Struggled with applying concepts to novel scenarios",
        "Incomplete explanation of electron transport chain",
        "Missed some key details about ATP synthesis",
        "Could improve on connecting concepts across different processes"
    ],
    recommendations: [
        "Review the electron transport chain using visual diagrams - focus on the flow of electrons and proton gradient formation",
        "Practice applying photosynthesis concepts to real-world scenarios like agriculture and climate change",
        "Create a comparison chart between photosynthesis and cellular respiration to strengthen connections",
        "Use spaced repetition to reinforce ATP synthesis mechanisms",
        "Watch video explanations of chemiosmosis to build intuition"
    ],
    summary: "You demonstrated a solid foundational understanding of photosynthesis and cellular respiration. Your ability to recall key facts and explain basic mechanisms is strong. To improve further, focus on the higher-order thinking skills - particularly applying these concepts to new situations and analyzing the connections between different biological processes. The electron transport chain and ATP synthesis mechanisms need more attention.",
    reportJson: {
        bloom_breakdown: {
            remember: 92,
            understand: 78,
            apply: 65,
            analyze: 58,
            evaluate: 70,
            create: 45
        },
        basic_score: 88,
        intermediate_score: 72,
        advanced_score: 55,
        questions_attempted: 8,
        questions_correct: 5,
        question_results: [
            {
                question_index: 0,
                question_text: "What is the overall equation for photosynthesis?",
                bloom_level: "remember",
                difficulty: "basic",
                user_answer_summary: "6CO2 + 6H2O + light energy → C6H12O6 + 6O2",
                score: 1.0,
                feedback: "Perfect! You correctly stated the complete balanced equation for photosynthesis.",
                is_correct: true,
                key_points_covered: ["Correct reactants (CO2 and H2O)", "Correct products (glucose and O2)", "Properly balanced equation", "Included light energy as input"],
                key_points_missed: [],
                improvement_tips: ""
            },
            {
                question_index: 1,
                question_text: "Explain the role of chlorophyll in the light-dependent reactions.",
                bloom_level: "understand",
                difficulty: "intermediate",
                user_answer_summary: "Chlorophyll absorbs light energy and uses it to excite electrons. These electrons are then passed through the electron transport chain.",
                score: 0.8,
                feedback: "Good explanation of chlorophyll's primary role. You could expand on the specific wavelengths absorbed and the photosystems involved.",
                is_correct: true,
                key_points_covered: ["Light absorption", "Electron excitation", "Connection to electron transport chain"],
                key_points_missed: ["Specific wavelengths (red and blue)", "Photosystem I and II distinction", "Role in water splitting"],
                improvement_tips: "Add details about how chlorophyll in Photosystem II splits water molecules, releasing oxygen as a byproduct."
            },
            {
                question_index: 2,
                question_text: "If a plant is placed in an environment with only green light, predict what would happen to its rate of photosynthesis and explain why.",
                bloom_level: "apply",
                difficulty: "intermediate",
                user_answer_summary: "The rate would decrease because chlorophyll reflects green light instead of absorbing it.",
                score: 0.7,
                feedback: "Correct reasoning about green light reflection. However, the answer could be more complete regarding the impact on ATP and NADPH production.",
                is_correct: true,
                key_points_covered: ["Green light is reflected", "Reduced light absorption", "Lower photosynthesis rate"],
                key_points_missed: ["Quantitative impact on ATP/NADPH", "Effect on Calvin cycle", "Accessory pigments that might help"],
                improvement_tips: "Consider mentioning that accessory pigments like carotenoids can absorb some green light, though less efficiently than chlorophyll absorbs red/blue light."
            },
            {
                question_index: 3,
                question_text: "Describe the chemiosmotic mechanism of ATP synthesis in chloroplasts.",
                bloom_level: "understand",
                difficulty: "advanced",
                user_answer_summary: "Protons build up in the thylakoid space creating a gradient. ATP synthase uses this gradient to make ATP as protons flow back.",
                score: 0.6,
                feedback: "You understand the basic concept but missed key details about how the proton gradient is established and the specific components involved.",
                is_correct: null,
                key_points_covered: ["Proton gradient concept", "ATP synthase role", "Proton flow drives ATP synthesis"],
                key_points_missed: ["Electron transport chain's role in pumping protons", "Thylakoid membrane structure", "Specific protein complexes involved", "Comparison to mitochondrial process"],
                improvement_tips: "Study how the electron transport chain (including cytochrome b6f complex) actively pumps H+ ions from the stroma into the thylakoid lumen, creating the electrochemical gradient."
            },
            {
                question_index: 4,
                question_text: "What are the three stages of the Calvin cycle?",
                bloom_level: "remember",
                difficulty: "basic",
                user_answer_summary: "Carbon fixation, reduction, and regeneration of RuBP.",
                score: 1.0,
                feedback: "Excellent! You correctly identified all three stages of the Calvin cycle.",
                is_correct: true,
                key_points_covered: ["Carbon fixation stage", "Reduction stage", "Regeneration of RuBP"],
                key_points_missed: [],
                improvement_tips: ""
            },
            {
                question_index: 5,
                question_text: "Compare and contrast the light-dependent and light-independent reactions in terms of location, inputs, and outputs.",
                bloom_level: "analyze",
                difficulty: "intermediate",
                user_answer_summary: "Light reactions happen in thylakoids and need light, water. They produce ATP, NADPH, and oxygen. Calvin cycle is in stroma, uses CO2, ATP, NADPH to make glucose.",
                score: 0.75,
                feedback: "Good comparison covering the main points. You could be more precise about the cyclical nature of the processes and their interdependence.",
                is_correct: true,
                key_points_covered: ["Correct locations identified", "Key inputs listed", "Main outputs identified", "Basic distinction clear"],
                key_points_missed: ["Cyclical regeneration in Calvin cycle", "Continuous nature of light reactions", "Energy carrier cycling between stages"],
                improvement_tips: "Emphasize how ATP and NADPH from light reactions are 'spent' in the Calvin cycle and must be regenerated, creating a continuous cycle of energy transfer."
            },
            {
                question_index: 6,
                question_text: "Evaluate the statement: 'Plants only perform photosynthesis during the day and cellular respiration at night.'",
                bloom_level: "evaluate",
                difficulty: "advanced",
                user_answer_summary: "This is false. Plants do photosynthesis only in light, but they do cellular respiration all the time, day and night, because they always need ATP for cellular processes.",
                score: 0.85,
                feedback: "Excellent critical evaluation! You correctly identified the misconception and explained the continuous nature of cellular respiration.",
                is_correct: true,
                key_points_covered: ["Identified statement as false", "Photosynthesis requires light", "Respiration is continuous", "ATP need is constant"],
                key_points_missed: ["Net gas exchange differences day vs night", "Compensation point concept"],
                improvement_tips: "You could mention that during the day, photosynthesis rate usually exceeds respiration rate, so plants show net O2 release and CO2 uptake."
            },
            {
                question_index: 7,
                question_text: "Design an experiment to test how different CO2 concentrations affect the rate of photosynthesis in aquatic plants.",
                bloom_level: "create",
                difficulty: "advanced",
                user_answer_summary: "Use elodea plants in water with different amounts of baking soda for CO2. Count bubbles produced in each setup over the same time period under the same light.",
                score: 0.5,
                feedback: "Basic experimental design is sound, but lacks controls, replication details, and consideration of confounding variables.",
                is_correct: null,
                key_points_covered: ["Aquatic plant choice (elodea)", "Variable CO2 using bicarbonate", "Measurable outcome (bubble counting)"],
                key_points_missed: ["Control group specification", "Replication/sample size", "Temperature control", "Light intensity control", "Statistical analysis plan", "Potential confounding variables"],
                improvement_tips: "A complete experimental design should include: control group (no added CO2), at least 3 replicates per condition, controlled variables (temperature, light intensity, plant size), and a plan for statistical analysis of results."
            }
        ]
    },
    examSession: {
        document: { title: "Chapter 8: Photosynthesis and Cellular Respiration" },
        questionPaper: { numQuestions: 8, duration: 30 }
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

function QuestionCard({ question }: { question: QuestionResult; index: number }) {
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

export default function ResultsPreviewPage() {
    const router = useRouter()
    const report = MOCK_REPORT

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
            {/* Preview Banner */}
            <div className="max-w-4xl mx-auto mb-4">
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-center">
                    <p className="text-sm text-blue-700 font-medium">
                        UI Preview Mode - This is sample data for demonstration purposes
                    </p>
                </div>
            </div>

            <div className="max-w-4xl mx-auto space-y-6">
                {/* Header */}
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" onClick={() => router.back()}>
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
                    <Button variant="outline" onClick={() => router.back()}>
                        Go Back
                    </Button>
                    <Button onClick={() => router.push("/authenticated/chat")}>
                        Practice More in Chat
                    </Button>
                </div>
            </div>
        </div>
    )
}
