"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import {
    Zap,
    BookOpen,
    MessageSquare,
    Clock,
    FileText,
    Check,
    Loader2,
    ArrowLeft,
    Sparkles,
    Crown,
    Rocket
} from "lucide-react"
import { toast } from "sonner"
import { useCredits } from "@/hooks/useCredits"
import { createClient } from "@/lib/supabase/client"

// Plan definitions - must match backend (create-order/route.ts)
// Based on cost analysis: ~48% margin (India), ~50-60% margin (Global)
const PLANS = {
    india: {
        starter: {
            name: "Starter",
            price: 399,
            currency: "INR",
            symbol: "₹",
            minutes: 100,
            pages: 100,
            chatMessages: 500,
            description: "Perfect for getting started",
            icon: Zap,
            popular: false,
        },
        standard: {
            name: "Standard",
            price: 699,
            currency: "INR",
            symbol: "₹",
            minutes: 200,
            pages: 250,
            chatMessages: 1000,
            description: "Great for regular studying",
            icon: Rocket,
            popular: true,
        },
        achiever: {
            name: "Achiever",
            price: 1299,
            currency: "INR",
            symbol: "₹",
            minutes: 350,
            pages: 500,
            chatMessages: 1500,
            description: "For serious exam preparation",
            icon: Crown,
            popular: false,
        },
        topup: {
            name: "Voice Top-Up",
            price: 199,
            currency: "INR",
            symbol: "₹",
            minutes: 60,
            pages: 0,
            chatMessages: 0,
            description: "Add more voice minutes",
            icon: Clock,
            popular: false,
        },
    },
    global: {
        starter: {
            name: "Starter",
            price: 9.99,
            currency: "USD",
            symbol: "$",
            minutes: 120,
            pages: 150,
            chatMessages: 500,
            description: "Perfect for getting started",
            icon: Zap,
            popular: false,
        },
        standard: {
            name: "Standard",
            price: 19.99,
            currency: "USD",
            symbol: "$",
            minutes: 250,
            pages: 350,
            chatMessages: 1000,
            description: "Great for regular studying",
            icon: Rocket,
            popular: true,
        },
        achiever: {
            name: "Achiever",
            price: 29.99,
            currency: "USD",
            symbol: "$",
            minutes: 400,
            pages: 700,
            chatMessages: 1500,
            description: "For serious exam preparation",
            icon: Crown,
            popular: false,
        },
        topup: {
            name: "Voice Top-Up",
            price: 5.99,
            currency: "USD",
            symbol: "$",
            minutes: 60,
            pages: 0,
            chatMessages: 0,
            description: "Add more voice minutes",
            icon: Clock,
            popular: false,
        },
    },
}

type Region = "india" | "global"
type PlanKey = keyof typeof PLANS.india | keyof typeof PLANS.global

declare global {
    interface Window {
        Razorpay: new (options: RazorpayOptions) => RazorpayInstance
    }
}

interface RazorpayOptions {
    key: string
    amount: number
    currency: string
    name: string
    description: string
    order_id: string
    handler: (response: RazorpayResponse) => void
    prefill?: {
        email?: string
        name?: string
    }
    theme?: {
        color?: string
    }
    modal?: {
        ondismiss?: () => void
    }
}

interface RazorpayInstance {
    open: () => void
    close: () => void
}

interface RazorpayResponse {
    razorpay_payment_id: string
    razorpay_order_id: string
    razorpay_signature: string
}

export default function PricingPage() {
    const router = useRouter()
    const { credits, loading: creditsLoading, refetch: refetchCredits } = useCredits(0) // No auto-refresh
    const [region, setRegion] = useState<Region>("india")
    const [processingPlan, setProcessingPlan] = useState<string | null>(null)
    const [userEmail, setUserEmail] = useState<string>("")

    // Load Razorpay script
    useEffect(() => {
        const script = document.createElement("script")
        script.src = "https://checkout.razorpay.com/v1/checkout.js"
        script.async = true
        document.body.appendChild(script)
        return () => {
            document.body.removeChild(script)
        }
    }, [])

    // Get user email and region
    useEffect(() => {
        async function getUserData() {
            const supabase = createClient()
            const { data: { user } } = await supabase.auth.getUser()
            if (user?.email) {
                setUserEmail(user.email)
            }
            // Check cookie for region (set by geo-detection middleware)
            const regionCookie = document.cookie
                .split("; ")
                .find(row => row.startsWith("region="))
                ?.split("=")[1]
            if (regionCookie === "global" || regionCookie === "india") {
                setRegion(regionCookie)
            }
        }
        getUserData()
    }, [])

    const handlePurchase = async (planKey: PlanKey) => {
        setProcessingPlan(planKey)

        try {
            // Create order
            const response = await fetch("/api/payment/create-order", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ planName: planKey }),
            })

            const data = await response.json()

            if (!data.success) {
                throw new Error(data.error || "Failed to create order")
            }

            // Open Razorpay checkout
            const options: RazorpayOptions = {
                key: data.keyId,
                amount: data.amount,
                currency: data.currency,
                name: "VOXAM",
                description: `${data.planName} - ${data.minutes} voice minutes`,
                order_id: data.orderId,
                handler: async function (response: RazorpayResponse) {
                    // Payment successful - webhook will credit the account
                    toast.success("Payment successful! Credits will be added shortly.", {
                        description: `Order ID: ${response.razorpay_order_id}`,
                    })

                    // Refetch credits after a delay (webhook processing)
                    setTimeout(() => {
                        refetchCredits()
                    }, 3000)

                    setProcessingPlan(null)
                },
                prefill: {
                    email: userEmail,
                },
                theme: {
                    color: "#0066FF",
                },
                modal: {
                    ondismiss: function () {
                        setProcessingPlan(null)
                    },
                },
            }

            const rzp = new window.Razorpay(options)
            rzp.open()
        } catch (error) {
            console.error("Purchase error:", error)
            toast.error("Failed to initiate payment", {
                description: error instanceof Error ? error.message : "Please try again",
            })
            setProcessingPlan(null)
        }
    }

    const plans = region === "india" ? PLANS.india : PLANS.global
    const planKeys = Object.keys(plans) as PlanKey[]

    return (
        <div className="min-h-screen bg-gradient-to-b from-background to-muted/30 p-4 md:p-8">
            <div className="max-w-6xl mx-auto space-y-8">
                {/* Header */}
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" onClick={() => router.back()}>
                        <ArrowLeft className="h-5 w-5" />
                    </Button>
                    <div>
                        <h1 className="text-3xl font-bold">Add Credits</h1>
                        <p className="text-muted-foreground">Choose a plan to continue your learning journey</p>
                    </div>
                </div>

                {/* Current Balance */}
                <Card className="border-2 border-primary/20 bg-gradient-to-r from-blue-50 to-violet-50">
                    <CardHeader className="pb-2">
                        <CardTitle className="flex items-center gap-2 text-lg">
                            <Sparkles className="h-5 w-5 text-primary" />
                            Your Current Balance
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        {creditsLoading ? (
                            <div className="flex items-center gap-2 text-muted-foreground">
                                <Loader2 className="h-4 w-4 animate-spin" />
                                Loading...
                            </div>
                        ) : credits ? (
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                {/* Voice Minutes */}
                                <div className="flex items-center gap-3 p-3 rounded-lg bg-white/50">
                                    <Clock className="h-5 w-5 text-primary" />
                                    <div>
                                        <p className="text-xs text-muted-foreground">Voice Minutes</p>
                                        <p className="text-lg font-bold">{credits.voiceMinutes.remaining} <span className="text-sm font-normal">mins</span></p>
                                    </div>
                                </div>

                                {/* Pages */}
                                <div className="flex items-center gap-3 p-3 rounded-lg bg-white/50">
                                    <FileText className="h-5 w-5 text-blue-500" />
                                    <div>
                                        <p className="text-xs text-muted-foreground">Document Pages</p>
                                        <p className="text-lg font-bold">{credits.pages.remaining} <span className="text-sm font-normal">pages</span></p>
                                    </div>
                                </div>

                                {/* Chat Messages */}
                                <div className="flex items-center gap-3 p-3 rounded-lg bg-white/50">
                                    <MessageSquare className="h-5 w-5 text-green-500" />
                                    <div>
                                        <p className="text-xs text-muted-foreground">Chat</p>
                                        <p className="text-lg font-bold">{credits.chatMessages.remaining >= 999999 ? "Unlimited" : credits.chatMessages.remaining}</p>
                                    </div>
                                </div>
                            </div>
                        ) : (
                            <p className="text-muted-foreground">Unable to load balance</p>
                        )}
                    </CardContent>
                </Card>

                {/* Region Toggle */}
                <div className="flex items-center justify-center gap-2">
                    <span className={`text-sm ${region === "india" ? "font-medium" : "text-muted-foreground"}`}>
                        India (INR)
                    </span>
                    <button
                        onClick={() => setRegion(r => r === "india" ? "global" : "india")}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                            region === "global" ? "bg-primary" : "bg-muted"
                        }`}
                    >
                        <span
                            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                                region === "global" ? "translate-x-6" : "translate-x-1"
                            }`}
                        />
                    </button>
                    <span className={`text-sm ${region === "global" ? "font-medium" : "text-muted-foreground"}`}>
                        Global (USD)
                    </span>
                </div>

                {/* Pricing Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                    {planKeys.map((key) => {
                        const plan = plans[key as keyof typeof plans]
                        if (!plan) return null
                        const Icon = plan.icon
                        const isProcessing = processingPlan === key

                        return (
                            <Card
                                key={key}
                                className={`relative overflow-hidden transition-all hover:shadow-lg ${
                                    plan.popular ? "border-2 border-primary shadow-md" : ""
                                }`}
                            >
                                {plan.popular && (
                                    <div className="absolute top-0 right-0">
                                        <Badge className="rounded-none rounded-bl-lg bg-primary">
                                            Most Popular
                                        </Badge>
                                    </div>
                                )}

                                <CardHeader className="pb-2">
                                    <div className="flex items-center gap-2">
                                        <div className={`p-2 rounded-lg ${plan.popular ? "bg-primary/10 text-primary" : "bg-muted"}`}>
                                            <Icon className="h-5 w-5" />
                                        </div>
                                        <CardTitle className="text-lg">{plan.name}</CardTitle>
                                    </div>
                                    <CardDescription>{plan.description}</CardDescription>
                                </CardHeader>

                                <CardContent className="space-y-4">
                                    {/* Price */}
                                    <div className="flex items-baseline gap-1">
                                        <span className="text-3xl font-bold">
                                            {plan.symbol}{plan.price}
                                        </span>
                                        <span className="text-muted-foreground text-sm">
                                            {plan.currency}
                                        </span>
                                    </div>

                                    <Separator />

                                    {/* Features */}
                                    <ul className="space-y-2">
                                        <li className="flex items-center gap-2 text-sm">
                                            <Check className="h-4 w-4 text-green-500 shrink-0" />
                                            <span><strong>{plan.minutes}</strong> voice minutes</span>
                                        </li>
                                        {plan.pages > 0 && (
                                            <li className="flex items-center gap-2 text-sm">
                                                <Check className="h-4 w-4 text-green-500 shrink-0" />
                                                <span><strong>{plan.pages}</strong> document pages</span>
                                            </li>
                                        )}
                                        {plan.chatMessages > 0 && (
                                            <li className="flex items-center gap-2 text-sm">
                                                <Check className="h-4 w-4 text-green-500 shrink-0" />
                                                <span><strong>{plan.chatMessages.toLocaleString()}</strong> chat messages</span>
                                            </li>
                                        )}
                                        <li className="flex items-center gap-2 text-sm">
                                            <Check className="h-4 w-4 text-green-500 shrink-0" />
                                            <span>AI feedback reports</span>
                                        </li>
                                    </ul>

                                    {/* CTA Button */}
                                    <Button
                                        className="w-full"
                                        variant={plan.popular ? "default" : "outline"}
                                        disabled={isProcessing || !!processingPlan}
                                        onClick={() => handlePurchase(key as PlanKey)}
                                    >
                                        {isProcessing ? (
                                            <>
                                                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                                Processing...
                                            </>
                                        ) : (
                                            <>
                                                <BookOpen className="h-4 w-4 mr-2" />
                                                Get {plan.name}
                                            </>
                                        )}
                                    </Button>
                                </CardContent>
                            </Card>
                        )
                    })}
                </div>

                {/* FAQ / Info */}
                <Card className="mt-8">
                    <CardHeader>
                        <CardTitle className="text-lg">How it works</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3 text-sm text-muted-foreground">
                        <p>
                            <strong className="text-foreground">Voice Minutes:</strong> Used for AI-powered voice exams and learning sessions.
                            Each minute of conversation with the AI tutor deducts from your balance.
                        </p>
                        <p>
                            <strong className="text-foreground">Document Pages:</strong> Upload study materials for AI processing.
                            Each page of your PDFs or documents counts toward this limit.
                        </p>
                        <p>
                            <strong className="text-foreground">Chat Messages:</strong> Paid plans include unlimited text-based chat with your documents.
                        </p>
                        <p className="text-xs pt-2 border-t">
                            Credits never expire. Secure payments powered by Razorpay.
                        </p>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
