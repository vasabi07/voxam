"use client";

/**
 * QuickActions - Provides quick action buttons that send prompts to the chat.
 *
 * Uses callback prop to send messages to the parent component.
 */

interface QuickActionsProps {
  onSendMessage: (message: string) => void
  disabled?: boolean
}

export function QuickActions({ onSendMessage, disabled }: QuickActionsProps) {
  return (
    <div className="flex gap-2 flex-wrap">
      <button
        onClick={() => onSendMessage("I want to create an exam")}
        disabled={disabled}
        className="px-3 py-1.5 bg-amber-100 hover:bg-amber-200 text-amber-800 rounded-md text-sm font-medium transition-colors disabled:opacity-50"
      >
        Create Exam
      </button>
      <button
        onClick={() => onSendMessage("I want to upload a document")}
        disabled={disabled}
        className="px-3 py-1.5 bg-blue-100 hover:bg-blue-200 text-blue-800 rounded-md text-sm font-medium transition-colors disabled:opacity-50"
      >
        Upload Document
      </button>
    </div>
  );
}
