"use server";

import { db } from "@/lib/prisma";
import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";

export type CreateQPParams = {
    documentId: string;
    duration: number;
    difficulty: string[];
    bloomLevel: string[];
    questionTypes: string[];
};

/**
 * Create a QuestionPaper record
 *
 * SECURITY: userId is derived from session, not from client input (IDOR fix)
 */
export async function createQuestionPaper(params: CreateQPParams) {
    try {
        // Get authenticated user from session
        const supabase = await createClient();
        const { data: { user } } = await supabase.auth.getUser();

        if (!user) {
            return { success: false, error: "Not authenticated" };
        }

        // Verify user owns the document
        const document = await db.document.findUnique({
            where: { id: params.documentId },
            select: { userId: true }
        });

        if (!document) {
            return { success: false, error: "Document not found" };
        }

        if (document.userId !== user.id) {
            return { success: false, error: "Unauthorized" };
        }

        const qp = await db.questionPaper.create({
            data: {
                documentId: params.documentId,
                userId: user.id, // Use authenticated user ID
                duration: params.duration,
                difficulty: params.difficulty,
                bloomLevel: params.bloomLevel,
                questionTypes: params.questionTypes,
                status: "PENDING",
            },
        });

        revalidatePath("/authenticated/exam");
        return { success: true, qpId: qp.id };
    } catch (error) {
        console.error("Failed to create QP record:", error);
        return { success: false, error: "Failed to initialize exam generation." };
    }
}
