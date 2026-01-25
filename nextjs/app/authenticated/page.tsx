"use client"

import Link from "next/link"
import { useCredits } from "@/hooks/useCredits"
import { Clock, MessageSquare, FileText, BarChart3, Upload, GraduationCap, Settings } from "lucide-react"

export default function DashboardPage() {
  const { credits, loading } = useCredits()

  return (
    <div className="p-4">
      <div className="flex flex-wrap justify-between gap-3 mb-6">
        <div className="flex min-w-72 flex-col gap-3">
          <h1 className="text-foreground tracking-tight text-3xl font-bold">Dashboard</h1>
          <p className="text-muted-foreground text-sm">Overview of your VoiceExam activity</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-card rounded-xl p-6 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-muted-foreground text-sm">Voice Minutes</p>
              <p className="text-foreground text-2xl font-bold">
                {loading ? "..." : credits ? `${credits.voiceMinutes.used}/${credits.voiceMinutes.limit}` : "0/0"}
              </p>
            </div>
            <Clock className="h-6 w-6 text-primary" />
          </div>
          {credits && (
            <div className="mt-3">
              <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-300"
                  style={{ width: `${Math.min((credits.voiceMinutes.used / credits.voiceMinutes.limit) * 100, 100)}%` }}
                />
              </div>
              <p className="text-muted-foreground text-xs mt-1">{credits.voiceMinutes.remaining} mins remaining</p>
            </div>
          )}
        </div>

        <div className="bg-card rounded-xl p-6 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-muted-foreground text-sm">Chat Messages</p>
              <p className="text-foreground text-2xl font-bold">
                {loading ? "..." : credits ? `${credits.chatMessages.used}/${credits.chatMessages.limit}` : "0/0"}
              </p>
            </div>
            <MessageSquare className="h-6 w-6 text-primary" />
          </div>
          {credits && (
            <div className="mt-3">
              <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-300"
                  style={{ width: `${Math.min((credits.chatMessages.used / credits.chatMessages.limit) * 100, 100)}%` }}
                />
              </div>
              <p className="text-muted-foreground text-xs mt-1">{credits.chatMessages.remaining} messages remaining</p>
            </div>
          )}
        </div>

        <div className="bg-card rounded-xl p-6 border border-border">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-muted-foreground text-sm">Document Pages</p>
              <p className="text-foreground text-2xl font-bold">
                {loading ? "..." : credits ? `${credits.pages.used}/${credits.pages.limit}` : "0/0"}
              </p>
            </div>
            <FileText className="h-6 w-6 text-primary" />
          </div>
          {credits && (
            <div className="mt-3">
              <div className="w-full h-2 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full bg-primary rounded-full transition-all duration-300"
                  style={{ width: `${Math.min((credits.pages.used / credits.pages.limit) * 100, 100)}%` }}
                />
              </div>
              <p className="text-muted-foreground text-xs mt-1">{credits.pages.remaining} pages remaining</p>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card rounded-xl p-6 border border-border">
          <h3 className="text-foreground text-lg font-bold mb-4">Recent Activity</h3>
          <div className="flex flex-col items-center justify-center py-12">
            <BarChart3 className="h-10 w-10 text-muted-foreground mb-4" />
            <p className="text-muted-foreground text-sm text-center">
              No recent activity yet
            </p>
            <p className="text-muted-foreground text-xs text-center mt-2">
              Upload documents and create exams to see your activity here
            </p>
          </div>
        </div>

        <div className="bg-card rounded-xl p-6 border border-border">
          <h3 className="text-foreground text-lg font-bold mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <Link
              href="/authenticated/documents"
              className="w-full flex items-center gap-3 p-3 bg-secondary hover:bg-secondary/80 rounded-lg transition-colors"
            >
              <Upload className="h-5 w-5 text-primary" />
              <div>
                <p className="text-foreground text-sm font-medium">Upload Document</p>
                <p className="text-muted-foreground text-xs">Add a new document for exam creation</p>
              </div>
            </Link>

            <Link
              href="/authenticated/examlist"
              className="w-full flex items-center gap-3 p-3 bg-secondary hover:bg-secondary/80 rounded-lg transition-colors"
            >
              <GraduationCap className="h-5 w-5 text-primary" />
              <div>
                <p className="text-foreground text-sm font-medium">Start Voice Exam</p>
                <p className="text-muted-foreground text-xs">Begin a new voice examination session</p>
              </div>
            </Link>

            <Link
              href="/authenticated/settings"
              className="w-full flex items-center gap-3 p-3 bg-secondary hover:bg-secondary/80 rounded-lg transition-colors"
            >
              <Settings className="h-5 w-5 text-primary" />
              <div>
                <p className="text-foreground text-sm font-medium">View Settings</p>
                <p className="text-muted-foreground text-xs">Configure your account preferences</p>
              </div>
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
