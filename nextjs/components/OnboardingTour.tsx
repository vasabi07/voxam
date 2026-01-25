"use client"

import { useEffect, useState, useCallback } from "react"
import { driver, type DriveStep, type Config } from "driver.js"
import "driver.js/dist/driver.css"
import { useSession } from "@/lib/auth-client"

const TOUR_STEPS: DriveStep[] = [
  {
    popover: {
      title: "Welcome to VOXAM!",
      description: "Let me show you around your AI-powered study companion. This quick tour will help you get started.",
      side: "over",
      align: "center",
    },
  },
  {
    element: '[data-tour="documents"]',
    popover: {
      title: "Upload Documents",
      description: "Start here by uploading your study materials. We support PDFs and images. Your documents will be processed and indexed for AI-powered learning.",
      side: "bottom",
      align: "center",
    },
  },
  {
    element: '[data-tour="chat"]',
    popover: {
      title: "Chat with Documents",
      description: "Ask questions about your study materials and get instant answers with page citations. Perfect for understanding complex concepts.",
      side: "bottom",
      align: "center",
    },
  },
  {
    element: '[data-tour="exam"]',
    popover: {
      title: "Take Voice Exams",
      description: "Test your knowledge with AI-generated voice-based exams. The AI tutor guides you through each question and provides instant feedback.",
      side: "bottom",
      align: "center",
    },
  },
  {
    element: '[data-tour="credits"]',
    popover: {
      title: "Manage Credits",
      description: "Track your usage and manage your credits here. Purchase more credits when needed to continue learning.",
      side: "bottom",
      align: "center",
    },
  },
  {
    element: '[data-tour="settings"]',
    popover: {
      title: "Settings",
      description: "Customize your experience here. You can also restart this tour anytime from settings.",
      side: "bottom",
      align: "center",
    },
  },
  {
    popover: {
      title: "You're All Set!",
      description: "Start by uploading a document to begin your learning journey. Happy studying!",
      side: "over",
      align: "center",
    },
  },
]

export function OnboardingTour() {
  const { data: session } = useSession()
  const [mounted, setMounted] = useState(false)

  const startTour = useCallback(() => {
    const driverObj = driver({
      showProgress: true,
      animate: true,
      allowClose: true,
      overlayColor: "rgba(0, 0, 0, 0.6)",
      stagePadding: 8,
      stageRadius: 8,
      popoverClass: "voxam-tour-popover",
      steps: TOUR_STEPS,
      nextBtnText: "Next",
      prevBtnText: "Back",
      doneBtnText: "Get Started",
      progressText: "{{current}} of {{total}}",
      onDestroyed: () => {
        if (session?.user?.id) {
          localStorage.setItem(`tour_completed_${session.user.id}`, "true")
        }
      },
    } as Config)

    driverObj.drive()
  }, [session?.user?.id])

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (!mounted || !session?.user?.id) return

    const hasCompletedTour = localStorage.getItem(`tour_completed_${session.user.id}`)
    if (!hasCompletedTour) {
      // Small delay to let the page render and navbar to mount
      const timer = setTimeout(startTour, 800)
      return () => clearTimeout(timer)
    }
  }, [session?.user?.id, mounted, startTour])

  return null
}

// Export function to restart tour (can be called from settings)
export function restartTour(userId: string) {
  localStorage.removeItem(`tour_completed_${userId}`)
  window.location.href = "/authenticated/documents"
}
