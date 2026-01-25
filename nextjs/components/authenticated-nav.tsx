"use client"

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
    MessageSquare,
    GraduationCap,
    FileText,
    LogOut,
    Mic,
    CreditCard,
    Settings
} from "lucide-react"
import { createClient } from '@/lib/supabase/client'
import { useRouter } from 'next/navigation'

export function AuthenticatedNavbar() {
    const pathname = usePathname()
    const router = useRouter()

    const handleSignOut = async () => {
        const supabase = createClient()
        await supabase.auth.signOut()
        router.refresh()
        router.push('/')
    }

    const navItems = [
        {
            name: 'Chat',
            href: '/authenticated/chat',
            icon: MessageSquare,
            tourId: 'chat'
        },
        {
            name: 'Exam',
            href: '/authenticated/exam',
            icon: GraduationCap,
            tourId: 'exam'
        },
        {
            name: 'Documents',
            href: '/authenticated/documents',
            icon: FileText,
            tourId: 'documents'
        },
        {
            name: 'Credits',
            href: '/authenticated/pricing',
            icon: CreditCard,
            tourId: 'credits'
        },
        {
            name: 'Settings',
            href: '/authenticated/settings',
            icon: Settings,
            tourId: 'settings'
        }
    ]

    return (
        <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur-md supports-backdrop-filter:bg-background/60">
            <div className="container mx-auto flex h-16 items-center justify-between px-4 md:px-6">
                <div className="flex items-center gap-2">
                    <Link href="/authenticated/chat" className="flex items-center gap-2">
                        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                            <Mic className="h-5 w-5" />
                        </div>
                        <span className="text-lg font-bold tracking-tight hidden sm:inline-block">VoiceExam AI</span>
                    </Link>
                </div>

                <nav className="flex items-center gap-1 sm:gap-2">
                    {navItems.map((item) => {
                        const Icon = item.icon
                        const isActive = pathname === item.href || pathname?.startsWith(item.href + '/')

                        return (
                            <Link key={item.href} href={item.href}>
                                <Button
                                    variant={isActive ? "secondary" : "ghost"}
                                    size="sm"
                                    data-tour={item.tourId}
                                    className={cn(
                                        "gap-2",
                                        isActive && "bg-secondary text-secondary-foreground"
                                    )}
                                >
                                    <Icon className="h-4 w-4" />
                                    <span className="hidden sm:inline-block">{item.name}</span>
                                </Button>
                            </Link>
                        )
                    })}
                </nav>

                <div className="flex items-center gap-2">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleSignOut}
                        className="text-muted-foreground hover:text-foreground"
                    >
                        <LogOut className="h-4 w-4 sm:mr-2" />
                        <span className="hidden sm:inline-block">Sign Out</span>
                    </Button>
                </div>
            </div>
        </header>
    )
}
