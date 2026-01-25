"use client"

import { AuthenticatedNavbar } from '@/components/authenticated-nav'
import { FeedbackWidget } from "@/components/FeedbackWidget"
import { OnboardingTour } from "@/components/OnboardingTour"

export default function AuthenticatedLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="relative flex h-screen w-full flex-col bg-background text-foreground overflow-hidden">
      <AuthenticatedNavbar />
      <main className="flex-1 min-h-0 overflow-auto">
        {children}
      </main>
      <OnboardingTour />
      <FeedbackWidget />
    </div>
  )
}
