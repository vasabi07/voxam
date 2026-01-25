"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import {
    User,
    Mail,
    Lock,
    Globe,
    CreditCard,
    Clock,
    FileText,
    MessageSquare,
    ArrowLeft,
    Loader2,
    Save,
    Eye,
    EyeOff,
    AlertTriangle,
    CheckCircle2,
    Sun,
    Moon,
    Monitor,
    Bell,
    BellOff,
} from "lucide-react"
import { toast } from "sonner"
import { createClient } from "@/lib/supabase/client"
import { useCredits } from "@/hooks/useCredits"
import { useSession } from "@/lib/auth-client"
import { useTheme } from "next-themes"
import { Switch } from "@/components/ui/switch"

export default function SettingsPage() {
    const router = useRouter()
    const { data: session } = useSession()
    const { credits, loading: creditsLoading, refetch: refetchCredits } = useCredits(0)
    const { theme, setTheme } = useTheme()
    const [mounted, setMounted] = useState(false)

    const [loading, setLoading] = useState(false)
    const [name, setName] = useState("")
    const [region, setRegion] = useState<"india" | "global">("india")

    // Notification preferences (stored in localStorage)
    const [emailNotifications, setEmailNotifications] = useState(true)
    const [examReminders, setExamReminders] = useState(true)
    const [progressUpdates, setProgressUpdates] = useState(true)

    // Password change
    const [currentPassword, setCurrentPassword] = useState("")
    const [newPassword, setNewPassword] = useState("")
    const [confirmPassword, setConfirmPassword] = useState("")
    const [showPasswords, setShowPasswords] = useState(false)
    const [changingPassword, setChangingPassword] = useState(false)

    // Check if user signed in with email (can change password) or OAuth
    const [isEmailUser, setIsEmailUser] = useState(false)

    // Handle hydration for theme
    useEffect(() => {
        setMounted(true)
    }, [])

    useEffect(() => {
        if (session?.user) {
            setName(session.user.user_metadata?.name || session.user.email?.split("@")[0] || "")

            // Check auth provider
            const provider = session.user.app_metadata?.provider
            setIsEmailUser(provider === "email")
        }

        // Get region from cookie
        const regionCookie = document.cookie
            .split("; ")
            .find(row => row.startsWith("region="))
            ?.split("=")[1]
        if (regionCookie === "global" || regionCookie === "india") {
            setRegion(regionCookie)
        }

        // Load notification preferences from localStorage
        const savedPrefs = localStorage.getItem("notificationPrefs")
        if (savedPrefs) {
            try {
                const prefs = JSON.parse(savedPrefs)
                setEmailNotifications(prefs.email ?? true)
                setExamReminders(prefs.examReminders ?? true)
                setProgressUpdates(prefs.progressUpdates ?? true)
            } catch (e) {
                // Ignore parse errors
            }
        }
    }, [session])

    const handleUpdateProfile = async () => {
        setLoading(true)
        try {
            const supabase = createClient()
            const { error } = await supabase.auth.updateUser({
                data: { name },
            })

            if (error) throw error

            toast.success("Profile updated!")
        } catch (error) {
            console.error("Update error:", error)
            toast.error("Failed to update profile", {
                description: error instanceof Error ? error.message : "Please try again",
            })
        } finally {
            setLoading(false)
        }
    }

    const handleChangePassword = async () => {
        if (newPassword !== confirmPassword) {
            toast.error("Passwords do not match")
            return
        }

        if (newPassword.length < 6) {
            toast.error("Password must be at least 6 characters")
            return
        }

        setChangingPassword(true)
        try {
            const supabase = createClient()
            const { error } = await supabase.auth.updateUser({
                password: newPassword,
            })

            if (error) throw error

            toast.success("Password changed successfully!")
            setCurrentPassword("")
            setNewPassword("")
            setConfirmPassword("")
        } catch (error) {
            console.error("Password change error:", error)
            toast.error("Failed to change password", {
                description: error instanceof Error ? error.message : "Please try again",
            })
        } finally {
            setChangingPassword(false)
        }
    }

    const handleRegionChange = (newRegion: "india" | "global") => {
        setRegion(newRegion)
        // Set cookie for 1 year
        document.cookie = `region=${newRegion}; path=/; max-age=31536000`
        toast.success(`Region set to ${newRegion === "india" ? "India" : "Global"}`)
    }

    const saveNotificationPrefs = (key: string, value: boolean) => {
        const savedPrefs = localStorage.getItem("notificationPrefs")
        let prefs = { email: emailNotifications, examReminders, progressUpdates }
        if (savedPrefs) {
            try {
                prefs = JSON.parse(savedPrefs)
            } catch (e) {}
        }
        prefs = { ...prefs, [key]: value }
        localStorage.setItem("notificationPrefs", JSON.stringify(prefs))
        toast.success("Preferences saved")
    }

    return (
        <div className="min-h-screen bg-background p-4 md:p-8">
            <div className="max-w-3xl mx-auto space-y-6">
                {/* Header */}
                <div className="flex items-center gap-4">
                    <Button variant="ghost" size="icon" onClick={() => router.back()}>
                        <ArrowLeft className="h-5 w-5" />
                    </Button>
                    <div>
                        <h1 className="text-2xl font-bold">Settings</h1>
                        <p className="text-muted-foreground">Manage your account and preferences</p>
                    </div>
                </div>

                {/* Profile Section */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <User className="h-5 w-5" />
                            Profile
                        </CardTitle>
                        <CardDescription>Your account information</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="email">Email</Label>
                            <div className="relative">
                                <Mail className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                                <Input
                                    id="email"
                                    type="email"
                                    value={session?.user?.email || ""}
                                    disabled
                                    className="pl-10 bg-muted"
                                />
                            </div>
                            <p className="text-xs text-muted-foreground">Email cannot be changed</p>
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="name">Display Name</Label>
                            <Input
                                id="name"
                                value={name}
                                onChange={(e) => setName(e.target.value)}
                                placeholder="Your name"
                            />
                        </div>

                        <Button onClick={handleUpdateProfile} disabled={loading}>
                            {loading ? (
                                <>
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                    Saving...
                                </>
                            ) : (
                                <>
                                    <Save className="h-4 w-4 mr-2" />
                                    Save Changes
                                </>
                            )}
                        </Button>
                    </CardContent>
                </Card>

                {/* Usage & Credits */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <CreditCard className="h-5 w-5" />
                            Usage & Credits
                        </CardTitle>
                        <CardDescription>Your current balance and usage</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        {creditsLoading ? (
                            <div className="flex items-center gap-2 text-muted-foreground">
                                <Loader2 className="h-4 w-4 animate-spin" />
                                Loading...
                            </div>
                        ) : credits ? (
                            <div className="space-y-4">
                                {/* Balance Cards */}
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                                    {/* Voice Minutes */}
                                    <div className="p-4 rounded-lg border bg-card">
                                        <div className="flex items-center gap-2 mb-2">
                                            <Clock className="h-4 w-4 text-primary" />
                                            <span className="text-sm text-muted-foreground">Voice Minutes</span>
                                        </div>
                                        <p className="text-2xl font-bold">
                                            {credits.voiceMinutes.remaining}
                                            <span className="text-sm font-normal text-muted-foreground ml-1">mins</span>
                                        </p>
                                    </div>

                                    {/* Pages */}
                                    <div className="p-4 rounded-lg border bg-card">
                                        <div className="flex items-center gap-2 mb-2">
                                            <FileText className="h-4 w-4 text-blue-500" />
                                            <span className="text-sm text-muted-foreground">Document Pages</span>
                                        </div>
                                        <p className="text-2xl font-bold">
                                            {credits.pages.remaining}
                                            <span className="text-sm font-normal text-muted-foreground ml-1">pages</span>
                                        </p>
                                    </div>

                                    {/* Chat Messages */}
                                    <div className="p-4 rounded-lg border bg-card">
                                        <div className="flex items-center gap-2 mb-2">
                                            <MessageSquare className="h-4 w-4 text-green-500" />
                                            <span className="text-sm text-muted-foreground">Chat</span>
                                        </div>
                                        <p className="text-2xl font-bold">
                                            {credits.chatMessages.remaining >= 999999 ? "Unlimited" : credits.chatMessages.remaining}
                                        </p>
                                    </div>
                                </div>

                                <Separator />

                                <Button variant="outline" onClick={() => router.push("/authenticated/pricing")}>
                                    <CreditCard className="h-4 w-4 mr-2" />
                                    Add More Credits
                                </Button>
                            </div>
                        ) : (
                            <p className="text-muted-foreground">Unable to load usage data</p>
                        )}
                    </CardContent>
                </Card>

                {/* Region Settings */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Globe className="h-5 w-5" />
                            Region
                        </CardTitle>
                        <CardDescription>
                            This affects pricing and voice service latency
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex gap-3">
                            <Button
                                variant={region === "india" ? "default" : "outline"}
                                onClick={() => handleRegionChange("india")}
                                className="flex-1"
                            >
                                {region === "india" && <CheckCircle2 className="h-4 w-4 mr-2" />}
                                India (INR)
                            </Button>
                            <Button
                                variant={region === "global" ? "default" : "outline"}
                                onClick={() => handleRegionChange("global")}
                                className="flex-1"
                            >
                                {region === "global" && <CheckCircle2 className="h-4 w-4 mr-2" />}
                                Global (USD)
                            </Button>
                        </div>
                        <p className="text-xs text-muted-foreground mt-2">
                            India region uses Google Cloud TTS for lower latency. Global uses Deepgram.
                        </p>
                    </CardContent>
                </Card>

                {/* Appearance */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Sun className="h-5 w-5" />
                            Appearance
                        </CardTitle>
                        <CardDescription>
                            Customize how VOXAM looks
                        </CardDescription>
                    </CardHeader>
                    <CardContent>
                        {mounted ? (
                            <div className="flex gap-3">
                                <Button
                                    variant={theme === "light" ? "default" : "outline"}
                                    onClick={() => setTheme("light")}
                                    className="flex-1"
                                >
                                    <Sun className="h-4 w-4 mr-2" />
                                    Light
                                </Button>
                                <Button
                                    variant={theme === "dark" ? "default" : "outline"}
                                    onClick={() => setTheme("dark")}
                                    className="flex-1"
                                >
                                    <Moon className="h-4 w-4 mr-2" />
                                    Dark
                                </Button>
                                <Button
                                    variant={theme === "system" ? "default" : "outline"}
                                    onClick={() => setTheme("system")}
                                    className="flex-1"
                                >
                                    <Monitor className="h-4 w-4 mr-2" />
                                    System
                                </Button>
                            </div>
                        ) : (
                            <div className="h-10 animate-pulse bg-muted rounded-md" />
                        )}
                    </CardContent>
                </Card>

                {/* Notifications */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Bell className="h-5 w-5" />
                            Notifications
                        </CardTitle>
                        <CardDescription>
                            Manage your notification preferences
                        </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                                <Label htmlFor="email-notifs" className="font-medium">Email Notifications</Label>
                                <p className="text-sm text-muted-foreground">
                                    Receive updates about your account via email
                                </p>
                            </div>
                            <Switch
                                id="email-notifs"
                                checked={emailNotifications}
                                onCheckedChange={(checked) => {
                                    setEmailNotifications(checked)
                                    saveNotificationPrefs("email", checked)
                                }}
                            />
                        </div>
                        <Separator />
                        <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                                <Label htmlFor="exam-reminders" className="font-medium">Exam Reminders</Label>
                                <p className="text-sm text-muted-foreground">
                                    Get notified about scheduled exams
                                </p>
                            </div>
                            <Switch
                                id="exam-reminders"
                                checked={examReminders}
                                onCheckedChange={(checked) => {
                                    setExamReminders(checked)
                                    saveNotificationPrefs("examReminders", checked)
                                }}
                            />
                        </div>
                        <Separator />
                        <div className="flex items-center justify-between">
                            <div className="space-y-0.5">
                                <Label htmlFor="progress-updates" className="font-medium">Progress Updates</Label>
                                <p className="text-sm text-muted-foreground">
                                    Weekly summary of your learning progress
                                </p>
                            </div>
                            <Switch
                                id="progress-updates"
                                checked={progressUpdates}
                                onCheckedChange={(checked) => {
                                    setProgressUpdates(checked)
                                    saveNotificationPrefs("progressUpdates", checked)
                                }}
                            />
                        </div>
                    </CardContent>
                </Card>

                {/* Password Change (only for email users) */}
                {isEmailUser && (
                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <Lock className="h-5 w-5" />
                                Change Password
                            </CardTitle>
                            <CardDescription>Update your account password</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="space-y-2">
                                <Label htmlFor="newPassword">New Password</Label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                                    <Input
                                        id="newPassword"
                                        type={showPasswords ? "text" : "password"}
                                        value={newPassword}
                                        onChange={(e) => setNewPassword(e.target.value)}
                                        placeholder="Enter new password"
                                        className="pl-10 pr-10"
                                        minLength={6}
                                    />
                                    <button
                                        type="button"
                                        className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                                        onClick={() => setShowPasswords(!showPasswords)}
                                    >
                                        {showPasswords ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                    </button>
                                </div>
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="confirmPassword">Confirm New Password</Label>
                                <div className="relative">
                                    <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                                    <Input
                                        id="confirmPassword"
                                        type={showPasswords ? "text" : "password"}
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        placeholder="Confirm new password"
                                        className="pl-10"
                                        minLength={6}
                                    />
                                </div>
                                {newPassword && confirmPassword && newPassword !== confirmPassword && (
                                    <p className="text-xs text-destructive">Passwords do not match</p>
                                )}
                            </div>

                            <Button
                                onClick={handleChangePassword}
                                disabled={changingPassword || !newPassword || newPassword !== confirmPassword}
                            >
                                {changingPassword ? (
                                    <>
                                        <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                        Changing...
                                    </>
                                ) : (
                                    "Change Password"
                                )}
                            </Button>
                        </CardContent>
                    </Card>
                )}

                {/* Danger Zone */}
                <Card className="border-destructive/50">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2 text-destructive">
                            <AlertTriangle className="h-5 w-5" />
                            Danger Zone
                        </CardTitle>
                        <CardDescription>Irreversible actions</CardDescription>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="font-medium">Delete Account</p>
                                <p className="text-sm text-muted-foreground">
                                    Permanently delete your account and all data
                                </p>
                            </div>
                            <Button
                                variant="destructive"
                                onClick={() => {
                                    toast.error("Account deletion coming soon", {
                                        description: "Please contact support to delete your account.",
                                    })
                                }}
                            >
                                Delete Account
                            </Button>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    )
}
