"use client"

import { useState } from "react"
import { MessageSquarePlus, X, Send, Bug, Lightbulb, MessageCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"
import { toast } from "sonner"

type FeedbackType = "bug" | "feature" | "general"

export function FeedbackWidget() {
  const [open, setOpen] = useState(false)
  const [type, setType] = useState<FeedbackType>("general")
  const [message, setMessage] = useState("")
  const [sending, setSending] = useState(false)

  const handleSubmit = async () => {
    if (!message.trim()) return

    setSending(true)
    try {
      const response = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          type,
          message: message.trim(),
          url: window.location.href,
        }),
      })

      if (!response.ok) {
        throw new Error("Failed to send feedback")
      }

      toast.success("Thanks for your feedback!", {
        description: "We'll review it shortly.",
      })

      setOpen(false)
      setMessage("")
      setType("general")
    } catch (error) {
      toast.error("Failed to send feedback", {
        description: "Please try again later.",
      })
    } finally {
      setSending(false)
    }
  }

  const types = [
    { id: "bug", icon: Bug, label: "Bug", color: "text-red-600" },
    { id: "feature", icon: Lightbulb, label: "Feature", color: "text-amber-600" },
    { id: "general", icon: MessageCircle, label: "General", color: "text-blue-600" },
  ] as const

  return (
    <>
      {/* Floating Button */}
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-50 p-3.5 rounded-full bg-primary text-primary-foreground shadow-lg hover:scale-105 hover:shadow-xl transition-all duration-200 group"
        aria-label="Send feedback"
      >
        <MessageSquarePlus className="w-5 h-5 group-hover:rotate-12 transition-transform" />
      </button>

      {/* Modal Overlay */}
      {open && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-in fade-in duration-200"
          onClick={(e) => {
            if (e.target === e.currentTarget) setOpen(false)
          }}
        >
          {/* Modal Content */}
          <div className="bg-background rounded-xl p-6 w-full max-w-md shadow-2xl border animate-in zoom-in-95 duration-200">
            {/* Header */}
            <div className="flex justify-between items-center mb-5">
              <h3 className="font-semibold text-lg">Send Feedback</h3>
              <button
                onClick={() => setOpen(false)}
                className="p-1.5 rounded-lg hover:bg-muted transition-colors"
                aria-label="Close"
              >
                <X className="w-5 h-5 text-muted-foreground" />
              </button>
            </div>

            {/* Type Selector */}
            <div className="flex gap-2 mb-4">
              {types.map(({ id, icon: Icon, label, color }) => (
                <button
                  key={id}
                  onClick={() => setType(id)}
                  className={cn(
                    "flex-1 flex flex-col items-center justify-center gap-1.5 py-3 rounded-lg border-2 transition-all",
                    type === id
                      ? "border-primary bg-primary/5"
                      : "border-muted hover:border-muted-foreground/30 hover:bg-muted/50"
                  )}
                >
                  <Icon className={cn("w-5 h-5", type === id ? color : "text-muted-foreground")} />
                  <span className={cn(
                    "text-xs font-medium",
                    type === id ? "text-foreground" : "text-muted-foreground"
                  )}>
                    {label}
                  </span>
                </button>
              ))}
            </div>

            {/* Message Input */}
            <Textarea
              placeholder={
                type === "bug"
                  ? "Describe the bug and steps to reproduce..."
                  : type === "feature"
                    ? "Describe the feature you'd like to see..."
                    : "Share your thoughts with us..."
              }
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={4}
              className="mb-4 resize-none"
              autoFocus
            />

            {/* Submit Button */}
            <Button
              onClick={handleSubmit}
              disabled={!message.trim() || sending}
              className="w-full"
            >
              {sending ? (
                "Sending..."
              ) : (
                <>
                  Send Feedback
                  <Send className="w-4 h-4 ml-2" />
                </>
              )}
            </Button>

            {/* Privacy Note */}
            <p className="text-xs text-muted-foreground text-center mt-3">
              Your feedback helps us improve VOXAM.
            </p>
          </div>
        </div>
      )}
    </>
  )
}
