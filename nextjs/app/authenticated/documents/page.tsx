"use client"

import { useState } from "react"
import { CloudUpload, FileText, Trash2, CheckCircle2, Clock, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"

// Dummy data type
type Document = {
  id: string
  name: string
  size: string
  date: string
  status: "ready" | "processing" | "failed"
  type: "pdf" | "docx" | "txt"
}

export default function DocumentsPage() {
  // Dummy state for documents
  const [documents, setDocuments] = useState<Document[]>([
    {
      id: "1",
      name: "Introduction to Psychology.pdf",
      size: "2.4 MB",
      date: "Oct 24, 2024",
      status: "ready",
      type: "pdf"
    },
    {
      id: "2",
      name: "Lecture Notes - Week 3.docx",
      size: "856 KB",
      date: "Oct 22, 2024",
      status: "processing",
      type: "docx"
    }
  ])

  const handleDelete = (id: string) => {
    setDocuments(documents.filter(doc => doc.id !== id))
  }

  return (
    <div className="flex flex-col gap-8 p-6 md:p-10 max-w-5xl mx-auto">

      {/* Header Section */}
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-bold text-[#1F2937] tracking-tight">Study Materials</h1>
        <p className="text-[#374151] text-base">
          Upload your notes, textbooks, or papers to generate exams.
        </p>
      </div>

      {/* Upload Zone (Ingestion) */}
      <div
        className="group relative flex flex-col items-center justify-center w-full h-48 rounded-xl border-2 border-dashed border-gray-300 bg-white hover:border-[#EA580C] transition-colors cursor-pointer shadow-sm"
      >
        <div className="flex flex-col items-center gap-3 text-center p-4">
          <div className="p-3 rounded-full bg-orange-50 text-[#EA580C] group-hover:scale-110 transition-transform">
            <CloudUpload className="w-6 h-6" />
          </div>
          <div className="flex flex-col gap-1">
            <p className="text-[#374151] font-medium">
              Click or drag files here
            </p>
            <p className="text-gray-400 text-sm">
              PDF, DOCX, TXT (Max 10MB)
            </p>
          </div>
        </div>
      </div>

      {/* Document List (The Binder) */}
      <div className="flex flex-col gap-4">
        <h2 className="text-lg font-semibold text-[#1F2937]">Your Binder</h2>

        {documents.length > 0 ? (
          <div className="flex flex-col gap-3">
            {documents.map((doc) => (
              <div
                key={doc.id}
                className="group flex items-center justify-between p-4 bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-all"
              >
                <div className="flex items-center gap-4">
                  {/* Icon */}
                  <div className="flex items-center justify-center w-10 h-10 rounded-full bg-orange-50 text-[#EA580C]">
                    <FileText className="w-5 h-5" />
                  </div>

                  {/* Info */}
                  <div className="flex flex-col gap-0.5">
                    <p className="text-[#374151] font-semibold text-sm md:text-base truncate max-w-[200px] md:max-w-md">
                      {doc.name}
                    </p>
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <span>{doc.size}</span>
                      <span>•</span>
                      <span>{doc.date}</span>
                    </div>
                  </div>
                </div>

                {/* Status & Actions */}
                <div className="flex items-center gap-4 md:gap-6">
                  {/* Status Badge */}
                  <div className={cn(
                    "px-2.5 py-0.5 rounded-full text-xs font-medium flex items-center gap-1.5",
                    doc.status === "ready" && "bg-green-50 text-green-700",
                    doc.status === "processing" && "bg-yellow-50 text-yellow-700",
                    doc.status === "failed" && "bg-red-50 text-red-700"
                  )}>
                    {doc.status === "ready" && <CheckCircle2 className="w-3 h-3" />}
                    {doc.status === "processing" && <Clock className="w-3 h-3 animate-pulse" />}
                    {doc.status === "failed" && <AlertCircle className="w-3 h-3" />}
                    <span className="capitalize">{doc.status}</span>
                  </div>

                  {/* Delete Action */}
                  <button
                    onClick={() => handleDelete(doc.id)}
                    className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                    aria-label="Delete document"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          /* Empty State */
          <div className="flex flex-col items-center justify-center py-12 text-center bg-white rounded-xl border border-gray-200 border-dashed">
            <div className="p-4 rounded-full bg-gray-50 mb-3">
              <FileText className="w-8 h-8 text-gray-300" />
            </div>
            <h3 className="text-[#374151] font-medium">Your library is empty</h3>
            <p className="text-gray-400 text-sm mt-1">
              Upload a document to start studying.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
