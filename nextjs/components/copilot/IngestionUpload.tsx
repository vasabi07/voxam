"use client";

import { useState, useEffect, useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { toast } from "sonner";
import { createClient } from "@/lib/supabase/client";
import { createDocumentRecord } from "@/app/actions/document";
import { UploadCloud, FileText, CheckCircle2, Loader2, AlertCircle } from "lucide-react";
import * as pdfjsLib from "pdfjs-dist";

// Set the worker source for pdf.js
pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;

/**
 * Extract page count from a PDF file using pdf.js
 */
async function getPageCount(file: File): Promise<number> {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
        return 0; // Can't count pages for non-PDF files
    }

    try {
        const arrayBuffer = await file.arrayBuffer();
        const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
        return pdf.numPages;
    } catch (error) {
        console.error("Error counting PDF pages:", error);
        return 0;
    }
}

interface IngestionUploadProps {
    isFromHistory?: boolean  // When true, render as read-only placeholder
}

export function IngestionUpload({ isFromHistory }: IngestionUploadProps) {
    const [uploadStatus, setUploadStatus] = useState<"IDLE" | "UPLOADING" | "PENDING" | "PROCESSING" | "READY" | "FAILED">("IDLE");
    const [docId, setDocId] = useState<string | null>(null);
    const [fileName, setFileName] = useState<string | null>(null);

    // Realtime Subscription
    useEffect(() => {
        if (!docId) return;

        const supabase = createClient();
        const channel = supabase
            .channel(`doc-${docId}`)
            .on(
                "postgres_changes",
                {
                    event: "UPDATE",
                    schema: "public",
                    table: "Document",
                    filter: `id=eq.${docId}`,
                },
                (payload) => {
                    const newStatus = payload.new.status;
                    setUploadStatus(newStatus);

                    if (newStatus === "READY") {
                        toast.success("Document Ingested Successfully!");
                    } else if (newStatus === "FAILED") {
                        toast.error("Ingestion Failed.");
                    }
                }
            )
            .subscribe();

        return () => {
            supabase.removeChannel(channel);
        };
    }, [docId]);

    const onDrop = useCallback(async (acceptedFiles: File[]) => {
        const file = acceptedFiles[0];
        if (!file) return;

        setFileName(file.name);
        setUploadStatus("UPLOADING");
        toast.info("Analyzing file...");

        try {
            // 1. Authenticate
            const supabase = createClient();
            const { data: { user } } = await supabase.auth.getUser();
            if (!user) {
                toast.error("Login required.");
                setUploadStatus("IDLE");
                return;
            }

            // 1b. Extract page count for PDFs (for credit check)
            const pageCount = await getPageCount(file);
            if (pageCount > 0) {
                toast.info(`Document has ${pageCount} pages`);
            }

            // Get auth session for API calls
            const { data: { session } } = await supabase.auth.getSession();
            if (!session?.access_token) {
                throw new Error("Not authenticated");
            }

            const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

            // 2. Get presigned URL from backend
            toast.info("Preparing upload...");
            const presignRes = await fetch(`${apiUrl}/upload/presign`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${session.access_token}`
                },
                body: JSON.stringify({
                    filename: file.name,
                    content_type: file.type
                }),
            });

            const presignData = await presignRes.json();
            if (!presignData.success) {
                throw new Error(presignData.error || "Failed to get upload URL");
            }

            const { upload_url, file_key: fileKey } = presignData;

            // 3. Upload file directly to R2
            toast.info("Uploading to storage...");
            const uploadRes = await fetch(upload_url, {
                method: "PUT",
                headers: {
                    "Content-Type": file.type,
                },
                body: file,
            });

            if (!uploadRes.ok) {
                throw new Error(`Upload failed: ${uploadRes.status}`);
            }

            toast.success("File uploaded!");

            // 4. Create DB Record (PENDING)
            const res = await createDocumentRecord({
                title: file.name,
                fileKey: fileKey,
                fileName: file.name,
                fileSize: file.size,
                mimeType: file.type,
                userId: user.id
            });

            if (!res.success || !res.docId) {
                throw new Error(res.error);
            }

            setDocId(res.docId);
            setUploadStatus("PENDING"); // Now waiting for processing

            // 5. Trigger Ingestion Agent
            const ingestRes = await fetch(`${apiUrl}/ingest`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${session.access_token}`
                },
                body: JSON.stringify({
                    file_key: fileKey,
                    document_id: res.docId,
                    page_count: pageCount  // Send page count for credit check
                }),
            });

            const ingestData = await ingestRes.json();
            if (ingestData.error) {
                // Credit check failed or other error
                toast.error(ingestData.error);
                setUploadStatus("FAILED");
                return;
            }

            setUploadStatus("PROCESSING");
            toast.info("Processing document...");

        } catch (e) {
            console.error(e);
            toast.error("Upload failed.");
            setUploadStatus("FAILED");
        }

    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { 'application/pdf': ['.pdf'], 'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'] },
        maxFiles: 1
    });

    // Historical view - show disabled placeholder for messages from previous sessions
    if (isFromHistory) {
        return (
            <div className="p-4 bg-muted/50 rounded-lg border border-dashed border-gray-300 w-full max-w-md">
                <p className="text-sm text-muted-foreground">
                    Upload form was shown here
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                    Type &quot;upload&quot; to upload a new document
                </p>
            </div>
        );
    }

    if (uploadStatus === "READY" && docId) {
        return (
            <div className="p-4 bg-green-50 rounded-xl border border-green-100 flex items-center gap-3 shadow-sm animate-in fade-in zoom-in w-full max-w-md">
                <CheckCircle2 className="text-green-600" size={20} />
                <div className="flex-1 overflow-hidden">
                    <p className="text-sm font-medium text-gray-800 truncate">{fileName}</p>
                    <p className="text-xs text-green-600">Ready for questions.</p>
                </div>
                <a
                    href={`/authenticated/documents/${docId}`}
                    className="px-3 py-1.5 bg-green-600 text-white text-xs font-medium rounded-lg hover:bg-green-700 transition-colors"
                >
                    Open
                </a>
            </div>
        );
    }

    return (
        <div className="w-full max-w-md bg-[#FAF9F6] rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            {uploadStatus === "IDLE" || uploadStatus === "FAILED" ? (
                <div
                    {...getRootProps()}
                    className={`p-6 border-2 border-dashed transition-colors cursor-pointer flex flex-col items-center justify-center text-center gap-2
                    ${isDragActive ? "border-[#0066FF] bg-blue-50/20" : "border-gray-300 hover:border-[#0066FF] hover:bg-white"}
                `}
                >
                    <input {...getInputProps()} />
                    <div className="p-3 bg-white rounded-full shadow-sm border border-gray-100">
                        <UploadCloud className="text-[#0066FF]" size={24} />
                    </div>
                    <div>
                        <p className="text-sm font-medium text-gray-700">Click or drag PDF/DOCX</p>
                        <p className="text-xs text-gray-500">Up to 10MB</p>
                    </div>
                </div>
            ) : (
                <div className="p-6 flex flex-col items-center gap-3">
                    <div className="p-3 bg-blue-50 rounded-full animate-pulse">
                        <Loader2 className="text-[#0066FF] animate-spin" size={24} />
                    </div>
                    <div className="text-center">
                        <p className="text-sm font-medium text-gray-800">
                            {uploadStatus === "UPLOADING" ? "Uploading..." : "Analyzing Content..."}
                        </p>
                        <p className="text-xs text-gray-500">{fileName}</p>
                    </div>
                    {/* Simple Progress Bar Visual */}
                    <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden">
                        <div className="h-full bg-[#0066FF] animate-progress-indeterminate rounded-full" />
                    </div>
                </div>
            )}
        </div>
    );
}
