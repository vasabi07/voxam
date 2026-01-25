"use server";

import { db } from "@/lib/prisma";
import { revalidatePath } from "next/cache";
import { createClient } from "@/lib/supabase/server";

export type CreateDocumentParams = {
    title: string;
    fileKey: string;
    fileName: string;
    fileSize: number;
    mimeType: string;
    userId: string;
};

/**
 * Get all documents for the authenticated user
 */
export async function getDocuments() {
    try {
        const supabase = await createClient();
        const { data: { user } } = await supabase.auth.getUser();

        if (!user) {
            return { success: false, error: "Not authenticated", documents: [] };
        }

        const documents = await db.document.findMany({
            where: {
                userId: user.id,
                archivedAt: null, // Only return non-archived documents
            },
            orderBy: { createdAt: "desc" },
            select: {
                id: true,
                title: true,
                fileName: true,
                fileSize: true,
                mimeType: true,
                status: true,
                createdAt: true,
                pageCount: true,
            },
        });

        return { success: true, documents };
    } catch (error) {
        console.error("Failed to fetch documents:", error);
        return { success: false, error: "Failed to fetch documents", documents: [] };
    }
}

/**
 * Delete a document and all associated data
 * Cleans up: Postgres, Neo4j, R2
 */
export async function deleteDocument(documentId: string) {
    try {
        const supabase = await createClient();
        const { data: { user } } = await supabase.auth.getUser();

        if (!user) {
            return { success: false, error: "Not authenticated" };
        }

        // First verify the document belongs to this user
        const document = await db.document.findUnique({
            where: { id: documentId },
            select: { userId: true, fileKey: true },
        });

        if (!document) {
            return { success: false, error: "Document not found" };
        }

        if (document.userId !== user.id) {
            return { success: false, error: "Unauthorized" };
        }

        // Call Python backend to handle Neo4j and R2 cleanup
        const { data: { session } } = await supabase.auth.getSession();
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

        const deleteRes = await fetch(`${apiUrl}/documents/${documentId}`, {
            method: "DELETE",
            headers: {
                "Authorization": `Bearer ${session?.access_token}`,
            },
        });

        if (!deleteRes.ok) {
            const errorData = await deleteRes.json();
            console.error("Backend deletion failed:", errorData);
            // Continue with Postgres deletion even if backend fails
        }

        // Delete from Postgres (cascades to related records)
        await db.document.delete({
            where: { id: documentId },
        });

        revalidatePath("/authenticated/documents");
        return { success: true };
    } catch (error) {
        console.error("Failed to delete document:", error);
        return { success: false, error: "Failed to delete document" };
    }
}

export async function createDocumentRecord(params: CreateDocumentParams) {
    try {
        const doc = await db.document.create({
            data: {
                title: params.title,
                fileKey: params.fileKey,
                fileName: params.fileName,
                fileSize: params.fileSize,
                mimeType: params.mimeType,
                userId: params.userId,
                status: "PENDING",
            },
        });

        revalidatePath("/authenticated/documents");
        return { success: true, docId: doc.id };
    } catch (error) {
        console.error("Failed to create Document record:", error);
        return { success: false, error: "Failed to start ingestion." };
    }
}

/**
 * Get detailed information about a single document
 * Includes related question papers and exam sessions
 */
export async function getDocumentDetails(documentId: string) {
    try {
        const supabase = await createClient();
        const { data: { user } } = await supabase.auth.getUser();

        if (!user) {
            return { success: false, error: "Not authenticated", document: null };
        }

        const document = await db.document.findUnique({
            where: { id: documentId },
            include: {
                questionPapers: {
                    orderBy: { createdAt: "desc" },
                    select: {
                        id: true,
                        status: true,
                        duration: true,
                        numQuestions: true,
                        difficulty: true,
                        questionTypes: true,
                        createdAt: true,
                    },
                },
                examSessions: {
                    orderBy: { createdAt: "desc" },
                    include: {
                        questionPaper: {
                            select: {
                                id: true,
                                numQuestions: true,
                                duration: true,
                            },
                        },
                        report: {
                            select: {
                                id: true,
                                score: true,
                                grade: true,
                            },
                        },
                    },
                },
                learnSessions: {
                    orderBy: { createdAt: "desc" },
                    take: 5,
                    select: {
                        id: true,
                        title: true,
                        status: true,
                        topicsCompleted: true,
                        topicsPlanned: true,
                        overallUnderstanding: true,
                        createdAt: true,
                        completedAt: true,
                    },
                },
            },
        });

        if (!document) {
            return { success: false, error: "Document not found", document: null };
        }

        if (document.userId !== user.id) {
            return { success: false, error: "Unauthorized", document: null };
        }

        return { success: true, document };
    } catch (error) {
        console.error("Failed to fetch document details:", error);
        return { success: false, error: "Failed to fetch document details", document: null };
    }
}

/**
 * Retry ingestion for a failed document
 */
export async function retryDocument(documentId: string) {
    try {
        const supabase = await createClient();
        const { data: { user } } = await supabase.auth.getUser();

        if (!user) {
            return { success: false, error: "Not authenticated" };
        }

        // First verify the document belongs to this user
        const document = await db.document.findUnique({
            where: { id: documentId },
            select: { userId: true, status: true },
        });

        if (!document) {
            return { success: false, error: "Document not found" };
        }

        if (document.userId !== user.id) {
            return { success: false, error: "Unauthorized" };
        }

        if (document.status !== "FAILED" && document.status !== "PENDING") {
            return { success: false, error: `Document is ${document.status}. Only FAILED or PENDING documents can be retried.` };
        }

        // Call Python backend to retry ingestion
        const { data: { session } } = await supabase.auth.getSession();
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

        const retryRes = await fetch(`${apiUrl}/documents/${documentId}/retry`, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${session?.access_token}`,
            },
        });

        const result = await retryRes.json();

        if (!result.success) {
            return { success: false, error: result.error || "Failed to retry" };
        }

        revalidatePath("/authenticated/documents");
        return { success: true, taskId: result.task_id };
    } catch (error) {
        console.error("Failed to retry document:", error);
        return { success: false, error: "Failed to retry document" };
    }
}

/**
 * Archive a document (soft delete)
 */
export async function archiveDocument(documentId: string) {
    try {
        const supabase = await createClient();
        const { data: { user } } = await supabase.auth.getUser();

        if (!user) {
            return { success: false, error: "Not authenticated" };
        }

        const document = await db.document.findUnique({
            where: { id: documentId },
            select: { userId: true },
        });

        if (!document) {
            return { success: false, error: "Document not found" };
        }

        if (document.userId !== user.id) {
            return { success: false, error: "Unauthorized" };
        }

        await db.document.update({
            where: { id: documentId },
            data: { archivedAt: new Date() },
        });

        revalidatePath("/authenticated/documents");
        return { success: true };
    } catch (error) {
        console.error("Failed to archive document:", error);
        return { success: false, error: "Failed to archive document" };
    }
}

/**
 * Restore an archived document
 */
export async function restoreDocument(documentId: string) {
    try {
        const supabase = await createClient();
        const { data: { user } } = await supabase.auth.getUser();

        if (!user) {
            return { success: false, error: "Not authenticated" };
        }

        const document = await db.document.findUnique({
            where: { id: documentId },
            select: { userId: true, archivedAt: true },
        });

        if (!document) {
            return { success: false, error: "Document not found" };
        }

        if (document.userId !== user.id) {
            return { success: false, error: "Unauthorized" };
        }

        if (!document.archivedAt) {
            return { success: false, error: "Document is not archived" };
        }

        await db.document.update({
            where: { id: documentId },
            data: { archivedAt: null },
        });

        revalidatePath("/authenticated/documents");
        return { success: true };
    } catch (error) {
        console.error("Failed to restore document:", error);
        return { success: false, error: "Failed to restore document" };
    }
}

/**
 * Get document file URL for viewing.
 * Returns a proxy URL that serves the PDF through our own server to avoid CORS issues.
 */
export async function getDocumentFileUrl(documentId: string) {
    try {
        const supabase = await createClient();
        const { data: { user } } = await supabase.auth.getUser();

        if (!user) {
            return { success: false, error: "Not authenticated", url: null };
        }

        const document = await db.document.findUnique({
            where: { id: documentId },
            select: { userId: true, fileKey: true, title: true },
        });

        if (!document) {
            return { success: false, error: "Document not found", url: null };
        }

        if (document.userId !== user.id) {
            return { success: false, error: "Unauthorized", url: null };
        }

        if (!document.fileKey) {
            return { success: false, error: "Document has no file", url: null };
        }

        // Return proxy URL to avoid CORS issues with R2
        // The proxy route at /api/documents/[id] handles authentication and fetches from R2
        return {
            success: true,
            url: `/api/documents/${documentId}`,
            title: document.title,
        };
    } catch (error) {
        console.error("Failed to get document URL:", error);
        return { success: false, error: "Failed to get document URL", url: null };
    }
}

/**
 * Get archived documents for the authenticated user
 */
export async function getArchivedDocuments() {
    try {
        const supabase = await createClient();
        const { data: { user } } = await supabase.auth.getUser();

        if (!user) {
            return { success: false, error: "Not authenticated", documents: [] };
        }

        const documents = await db.document.findMany({
            where: {
                userId: user.id,
                archivedAt: { not: null },
            },
            orderBy: { archivedAt: "desc" },
            select: {
                id: true,
                title: true,
                fileName: true,
                fileSize: true,
                mimeType: true,
                status: true,
                createdAt: true,
                pageCount: true,
                archivedAt: true,
            },
        });

        return { success: true, documents };
    } catch (error) {
        console.error("Failed to fetch archived documents:", error);
        return { success: false, error: "Failed to fetch archived documents", documents: [] };
    }
}
