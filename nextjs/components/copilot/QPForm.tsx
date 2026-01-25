"use client";

import { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { createClient } from "@/lib/supabase/client";
import { createQuestionPaper } from "@/app/actions/qp";
import { Loader2, CheckCircle2 } from "lucide-react";

type QPFormData = {
    duration: number;
    difficulty: string[];
    bloomLevel: string[];
    questionTypes: string[];
};

interface QPFormProps {
    docId: string
    isFromHistory?: boolean  // When true, render as read-only placeholder
}

export function QPForm({ docId, isFromHistory }: QPFormProps) { // docId is passed from Copilot Context?
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [qpStatus, setQpStatus] = useState<"IDLE" | "PENDING" | "PROCESSING" | "READY" | "FAILED">("IDLE");
    const [qpId, setQpId] = useState<string | null>(null);

    const { register, handleSubmit, watch, setValue } = useForm<QPFormData>({
        defaultValues: {
            duration: 30,
            difficulty: ["intermediate"],
            bloomLevel: ["understand", "apply"],
            questionTypes: ["multiple_choice", "long_answer"],
        },
    });

    const duration = watch("duration");

    // Subscribe to Realtime updates once we have a QPID
    useEffect(() => {
        if (!qpId) return;

        const supabase = createClient();
        const channel = supabase
            .channel(`qp-${qpId}`)
            .on(
                "postgres_changes",
                {
                    event: "UPDATE",
                    schema: "public",
                    table: "QuestionPaper",
                    filter: `id=eq.${qpId}`,
                },
                (payload) => {
                    const newStatus = payload.new.status;
                    setQpStatus(newStatus);

                    if (newStatus === "READY") {
                        toast.success("Question Paper Generated!", {
                            action: {
                                label: "Start Exam",
                                onClick: () => window.location.href = `/authenticated/exam/${qpId}` // Or trigger another action
                            }
                        });
                    } else if (newStatus === "FAILED") {
                        toast.error("Generation Failed. Please try again.");
                    }
                }
            )
            .subscribe();

        return () => {
            supabase.removeChannel(channel);
        };
    }, [qpId]);

    // Historical view - show disabled placeholder for messages from previous sessions
    if (isFromHistory) {
        return (
            <div className="p-4 bg-muted/50 rounded-lg border border-dashed border-gray-300">
                <p className="text-sm text-muted-foreground">
                    Question paper form was shown here
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                    Type &quot;create exam&quot; to start a new exam
                </p>
            </div>
        );
    }

    const onSubmit = async (data: QPFormData) => {
        setIsSubmitting(true);
        toast.info("Initializing exam generation...");

        // 1. Create Record in DB (PENDING)
        // We need userId. Copilot context usually has it, distinct from the 'user' prop?
        // For now assuming we can get it or the server action handles it via auth().
        // Actually server action should use auth() to get userId.
        // Let's assume we pass userId or it's inferred. server action usually handles auth.
        // I need to update server action to use `auth()` from Next.js headers/cookies if not passed.
        // But let's stick to the plan for now. I'll pass userId if available or let server resolve.
        // Wait, the client component doesn't have userId easily unless passed.
        // Copilot provides context.

        // Server action now gets userId from session automatically (IDOR fix)
        const res = await createQuestionPaper({
            ...data,
            documentId: docId,
        });

        if (!res.success || !res.qpId) {
            toast.error(res.error || "Failed to start.");
            setIsSubmitting(false);
            return;
        }

        setQpId(res.qpId);
        setQpStatus("PENDING");

        // 2. Trigger Backend Agent - call Python directly with auth
        try {
            const supabase = createClient();
            const { data: { session } } = await supabase.auth.getSession();
            if (!session?.access_token) {
                throw new Error("Not authenticated");
            }

            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
            await fetch(`${apiUrl}/create-qp`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${session.access_token}`
                },
                body: JSON.stringify({
                    qp_id: res.qpId,
                    document_id: docId,
                    duration: data.duration,
                    num_questions: 10, // Default
                    difficulty_levels: data.difficulty,
                    bloom_levels: data.bloomLevel,
                    question_types: data.questionTypes,
                }),
            });
            setQpStatus("PROCESSING");
        } catch (e) {
            console.error(e);
            toast.error("Failed to trigger agent.");
        }

        setIsSubmitting(false);
    };

    if (qpStatus === "READY") {
        return (
            <div className="p-6 bg-green-50 rounded-xl border border-green-100 flex flex-col items-center text-center gap-3 shadow-sm animate-in fade-in zoom-in">
                <div className="h-12 w-12 bg-green-100 text-green-600 rounded-full flex items-center justify-center">
                    <CheckCircle2 size={24} />
                </div>
                <h3 className="text-lg font-bold text-gray-800">Exam Ready!</h3>
                <p className="text-sm text-gray-600">Your question paper has been generated successfully.</p>
                <button
                    onClick={() => window.location.href = `/authenticated/exam/${qpId}`}
                    className="mt-2 w-full bg-green-600 text-white py-2 rounded-lg font-medium hover:bg-green-700 transition-colors"
                >
                    Start Exam
                </button>
            </div>
        );
    }

    return (
        <div className="p-5 bg-[#FAF9F6] rounded-xl border border-gray-200 shadow-sm w-full max-w-md">
            <h3 className="text-lg font-bold text-[#374151] mb-4">Configure Question Paper</h3>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">

                {/* Duration Slider */}
                <div className="space-y-2">
                    <div className="flex justify-between text-sm font-medium text-gray-600">
                        <label>Duration</label>
                        <span className="text-[#0066FF]">{duration} mins</span>
                    </div>
                    <input
                        type="range"
                        min="10"
                        max="120"
                        step="5"
                        {...register("duration", { valueAsNumber: true })}
                        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-[#0066FF]"
                    />
                </div>

                {/* Difficulty Chips */}
                <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-600">Difficulty</label>
                    <div className="flex flex-wrap gap-2">
                        {["basic", "intermediate", "advanced"].map(level => (
                            <button
                                key={level}
                                type="button"
                                onClick={() => setValue("difficulty", [level])} // Single select for simplicity for now? Or toggle. Let's do single select to match simple UX
                                className={`px-3 py-1 text-xs rounded-full border transition-colors ${watch("difficulty").includes(level)
                                    ? "bg-blue-50 border-blue-200 text-[#0066FF] font-medium"
                                    : "bg-white border-gray-200 text-gray-500 hover:bg-gray-50"
                                    }`}
                            >
                                {level.charAt(0).toUpperCase() + level.slice(1)}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Bloom Chips */}
                <div className="space-y-2">
                    <label className="text-sm font-medium text-gray-600">Cognitive Level</label>
                    <div className="flex flex-wrap gap-2">
                        {["remember", "understand", "apply", "analyze"].map(level => (
                            <button
                                key={level}
                                type="button"
                                onClick={() => {
                                    const current = watch("bloomLevel");
                                    if (current.includes(level)) setValue("bloomLevel", current.filter(l => l !== level));
                                    else setValue("bloomLevel", [...current, level]);
                                }}
                                className={`px-3 py-1 text-xs rounded-full border transition-colors ${watch("bloomLevel").includes(level)
                                    ? "bg-blue-50 border-blue-200 text-[#0066FF] font-medium"
                                    : "bg-white border-gray-200 text-gray-500 hover:bg-gray-50"
                                    }`}
                            >
                                {level.charAt(0).toUpperCase() + level.slice(1)}
                            </button>
                        ))}
                    </div>
                </div>

                <button
                    type="submit"
                    disabled={isSubmitting || qpStatus === "PROCESSING"}
                    className="w-full bg-[#0066FF] text-white py-2.5 rounded-lg font-medium hover:bg-[#0052CC] disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                >
                    {isSubmitting || qpStatus === "PROCESSING" ? (
                        <>
                            <Loader2 className="animate-spin" size={18} />
                            Generating...
                        </>
                    ) : (
                        "Create Question Paper"
                    )}
                </button>
            </form>
        </div>
    );
}
