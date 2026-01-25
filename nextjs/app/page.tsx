"use client"

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { motion, useScroll, useTransform, useInView } from 'motion/react'
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Mic,
  FileText,
  Brain,
  BarChart3,
  GraduationCap,
  Check,
  ArrowRight,
  Play,
  Sparkles,
  Zap,
  Target,
  Layers,
  Volume2,
  MessageSquare,
  Stethoscope,
  Scale,
  Cpu,
  Trophy,
  ChevronDown,
  type LucideIcon
} from "lucide-react"

// Animated Voice Waveform Component
function VoiceWaveform({ className = "" }: { className?: string }) {
  const bars = 48

  return (
    <div className={`flex items-center justify-center gap-[3px] h-32 ${className}`}>
      {Array.from({ length: bars }).map((_, i) => {
        const delay = i * 0.05
        const baseHeight = Math.sin(i * 0.3) * 30 + 50

        return (
          <motion.div
            key={i}
            className="w-1 rounded-full bg-gradient-to-t from-primary/40 via-primary to-accent"
            initial={{ height: 8 }}
            animate={{
              height: [8, baseHeight, 8],
              opacity: [0.4, 1, 0.4]
            }}
            transition={{
              duration: 1.2,
              delay: delay,
              repeat: Infinity,
              ease: "easeInOut"
            }}
          />
        )
      })}
    </div>
  )
}

// Floating Orb Component
function FloatingOrb({ delay = 0, size = 300, color = "primary" }: { delay?: number; size?: number; color?: string }) {
  const colorMap: Record<string, string> = {
    primary: "bg-primary/20",
    accent: "bg-accent/20",
    amber: "bg-amber-500/20"
  }

  return (
    <motion.div
      className={`absolute rounded-full blur-3xl ${colorMap[color]}`}
      style={{ width: size, height: size }}
      animate={{
        y: [-20, 20, -20],
        x: [-10, 10, -10],
        scale: [1, 1.1, 1]
      }}
      transition={{
        duration: 8,
        delay,
        repeat: Infinity,
        ease: "easeInOut"
      }}
    />
  )
}

// Feature Card with Hover Effect
function FeatureCard({
  icon: Icon,
  title,
  description,
  accent = "primary",
  delay = 0
}: {
  icon: LucideIcon
  title: string
  description: string
  accent?: "primary" | "accent" | "amber" | "emerald"
  delay?: number
}) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-100px" })

  const accentColors: Record<string, string> = {
    primary: "from-primary/20 to-transparent group-hover:from-primary/30",
    accent: "from-accent/20 to-transparent group-hover:from-accent/30",
    amber: "from-amber-500/20 to-transparent group-hover:from-amber-500/30",
    emerald: "from-emerald-500/20 to-transparent group-hover:from-emerald-500/30"
  }

  const iconColors: Record<string, string> = {
    primary: "text-primary",
    accent: "text-accent",
    amber: "text-amber-500",
    emerald: "text-emerald-500"
  }

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40 }}
      animate={isInView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay }}
    >
      <Card className="group relative overflow-hidden border-border/50 bg-card/50 backdrop-blur-sm transition-all duration-500 hover:border-primary/30 hover:shadow-xl hover:shadow-primary/5">
        <div className={`absolute inset-0 bg-gradient-to-br ${accentColors[accent]} transition-all duration-500`} />
        <CardHeader className="relative">
          <div className={`mb-4 w-14 h-14 rounded-2xl bg-secondary/80 flex items-center justify-center ${iconColors[accent]} transition-transform duration-300 group-hover:scale-110`}>
            <Icon className="h-7 w-7" />
          </div>
          <CardTitle className="text-xl tracking-tight">{title}</CardTitle>
        </CardHeader>
        <CardContent className="relative">
          <p className="text-muted-foreground leading-relaxed">{description}</p>
        </CardContent>
      </Card>
    </motion.div>
  )
}

// Stats Counter Component
function StatCounter({ value, label, suffix = "" }: { value: number; label: string; suffix?: string }) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true })
  const [count, setCount] = useState(0)

  useEffect(() => {
    if (isInView) {
      const duration = 2000
      const steps = 60
      const increment = value / steps
      let current = 0

      const timer = setInterval(() => {
        current += increment
        if (current >= value) {
          setCount(value)
          clearInterval(timer)
        } else {
          setCount(Math.floor(current))
        }
      }, duration / steps)

      return () => clearInterval(timer)
    }
  }, [isInView, value])

  return (
    <div ref={ref} className="text-center">
      <div className="text-5xl md:text-6xl font-bold tracking-tight text-gradient">
        {count.toLocaleString()}{suffix}
      </div>
      <div className="mt-2 text-muted-foreground">{label}</div>
    </div>
  )
}

// Pricing Card
function PricingCard({
  title,
  price,
  description,
  features,
  popular = false,
  delay = 0
}: {
  title: string
  price: string
  description: string
  features: string[]
  popular?: boolean
  delay?: number
}) {
  const ref = useRef(null)
  const isInView = useInView(ref, { once: true, margin: "-50px" })

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 40, scale: 0.95 }}
      animate={isInView ? { opacity: 1, y: 0, scale: 1 } : {}}
      transition={{ duration: 0.5, delay }}
      className="relative"
    >
      {popular && (
        <div className="absolute -top-4 left-1/2 -translate-x-1/2 z-10">
          <span className="px-4 py-1.5 rounded-full bg-primary text-primary-foreground text-sm font-medium">
            Most Popular
          </span>
        </div>
      )}
      <Card className={`relative overflow-hidden h-full transition-all duration-300 ${
        popular
          ? 'border-primary bg-card shadow-2xl shadow-primary/10 scale-105'
          : 'border-border/50 bg-card/50 hover:border-primary/30 hover:shadow-xl hover:shadow-primary/5'
      }`}>
        {popular && (
          <div className="absolute inset-0 bg-gradient-to-br from-primary/10 via-transparent to-accent/5" />
        )}
        <CardHeader className="relative text-center pb-2">
          <CardTitle className="text-2xl">{title}</CardTitle>
          <div className="mt-4">
            <span className="text-5xl font-bold tracking-tight">{price}</span>
          </div>
          <CardDescription className="mt-2">{description}</CardDescription>
        </CardHeader>
        <CardContent className="relative pt-6">
          <ul className="space-y-4">
            {features.map((feature, i) => (
              <li key={i} className="flex items-start gap-3">
                <Check className="h-5 w-5 text-primary shrink-0 mt-0.5" />
                <span className="text-muted-foreground">{feature}</span>
              </li>
            ))}
          </ul>
          <Link href="/login" className="block mt-8">
            <Button
              className={`w-full h-12 text-base font-medium ${
                popular ? '' : 'bg-secondary hover:bg-secondary/80 text-foreground'
              }`}
              variant={popular ? "default" : "secondary"}
            >
              Get Started
            </Button>
          </Link>
        </CardContent>
      </Card>
    </motion.div>
  )
}

export default function Home() {
  const heroRef = useRef(null)
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"]
  })

  const heroOpacity = useTransform(scrollYProgress, [0, 0.5], [1, 0])
  const heroScale = useTransform(scrollYProgress, [0, 0.5], [1, 0.95])
  const heroY = useTransform(scrollYProgress, [0, 0.5], [0, 100])

  return (
    <div className="min-h-screen bg-background text-foreground overflow-x-hidden">
      {/* Noise Overlay */}
      <div className="noise-overlay" />

      {/* Header */}
      <header className="fixed top-0 z-50 w-full">
        <div className="absolute inset-0 bg-background/60 backdrop-blur-xl border-b border-border/40" />
        <div className="relative container mx-auto flex h-20 items-center justify-between px-6">
          <Link href="/" className="flex items-center gap-3 group">
            <div className="relative">
              <div className="absolute inset-0 bg-primary/50 blur-xl opacity-0 group-hover:opacity-100 transition-opacity" />
              <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
                <Volume2 className="h-5 w-5" />
              </div>
            </div>
            <span className="text-xl font-bold tracking-tight">VOXAM</span>
          </Link>

          <nav className="hidden md:flex items-center gap-10 text-sm font-medium text-muted-foreground">
            <button
              onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })}
              className="hover:text-foreground transition-colors"
            >
              Features
            </button>
            <button
              onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })}
              className="hover:text-foreground transition-colors"
            >
              How it Works
            </button>
            <button
              onClick={() => document.getElementById('pricing')?.scrollIntoView({ behavior: 'smooth' })}
              className="hover:text-foreground transition-colors"
            >
              Pricing
            </button>
          </nav>

          <div className="flex items-center gap-4">
            <Link href="/login">
              <Button className="rounded-full px-6 h-11 font-medium">
                Start Free
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main>
        {/* Hero Section */}
        <section ref={heroRef} className="relative min-h-screen flex items-center justify-center overflow-hidden pt-20">
          {/* Background Effects */}
          <div className="absolute inset-0">
            <FloatingOrb delay={0} size={500} color="primary" />
            <FloatingOrb delay={2} size={400} color="accent" />
            <FloatingOrb delay={4} size={300} color="amber" />
            <div className="absolute top-1/4 left-1/4">
              <FloatingOrb delay={1} size={200} color="primary" />
            </div>
            <div className="absolute bottom-1/4 right-1/4">
              <FloatingOrb delay={3} size={250} color="accent" />
            </div>
          </div>

          {/* Grid Pattern */}
          <div
            className="absolute inset-0 opacity-[0.02]"
            style={{
              backgroundImage: `linear-gradient(rgba(255,255,255,0.1) 1px, transparent 1px),
                               linear-gradient(90deg, rgba(255,255,255,0.1) 1px, transparent 1px)`,
              backgroundSize: '60px 60px'
            }}
          />

          <motion.div
            className="relative container mx-auto px-6 text-center"
            style={{ opacity: heroOpacity, scale: heroScale, y: heroY }}
          >
            <motion.div
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.2 }}
            >
              <span className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-secondary/80 border border-border/50 text-sm font-medium text-muted-foreground mb-4">
                <Sparkles className="h-4 w-4 text-primary" />
                AI-Powered Voice Examinations
              </span>
            </motion.div>

            <motion.h1
              className="text-5xl sm:text-6xl md:text-7xl lg:text-8xl font-bold tracking-tight leading-[1.1] mb-8"
              initial={{ opacity: 0, y: 30 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.4 }}
            >
              Learn by
              <br />
              <span className="text-gradient">Speaking</span>
            </motion.h1>

            {/* Voice Waveform */}
            <motion.div
              className="my-5 md:my-6"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 1, delay: 0.6 }}
            >
              <VoiceWaveform />
            </motion.div>

            <motion.p
              className="max-w-xl mx-auto text-xl md:text-2xl text-foreground/90 font-medium mb-3"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.8 }}
            >
              Stop re-reading notes. Start explaining them.
            </motion.p>

            <motion.p
              className="max-w-2xl mx-auto text-lg text-muted-foreground leading-relaxed mb-8"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 0.95 }}
            >
              Traditional studying is passive. VOXAM makes it active. Upload your
              materials, have real conversations with AI, and discover what you
              actually know — before your exam does.
            </motion.p>

            <motion.div
              className="flex flex-col sm:flex-row items-center justify-center gap-4"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.8, delay: 1 }}
            >
              <Link href="/login">
                <Button size="lg" className="h-14 rounded-full px-8 text-base font-medium glow-blue">
                  Start Your Free Exam
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
              <Button
                size="lg"
                variant="outline"
                className="h-14 rounded-full px-8 text-base font-medium border-border/50 hover:bg-secondary/50"
              >
                <Play className="mr-2 h-5 w-5" />
                Watch Demo
              </Button>
            </motion.div>
          </motion.div>

          {/* Scroll Indicator */}
          <motion.div
            className="absolute bottom-10 left-1/2 -translate-x-1/2"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.5 }}
          >
            <motion.div
              className="w-6 h-10 rounded-full border-2 border-muted-foreground/30 flex items-start justify-center p-2"
              animate={{ y: [0, 5, 0] }}
              transition={{ duration: 1.5, repeat: Infinity }}
            >
              <motion.div
                className="w-1.5 h-1.5 rounded-full bg-primary"
                animate={{ y: [0, 16, 0], opacity: [1, 0.5, 1] }}
                transition={{ duration: 1.5, repeat: Infinity }}
              />
            </motion.div>
          </motion.div>
        </section>

        {/* Features Section */}
        <section id="features" className="py-32 relative">
          <div className="container mx-auto px-6">
            <motion.div
              className="text-center mb-20"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              <span className="text-primary font-medium mb-4 block">Features</span>
              <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-6">
                Voice-First Learning
              </h2>
              <p className="max-w-2xl mx-auto text-lg text-muted-foreground">
                Experience education reimagined. Our AI understands not just what you say,
                but how deeply you understand it.
              </p>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              <FeatureCard
                icon={Mic}
                title="Real-time Voice Exams"
                description="Feels like talking to a real tutor — instant responses, natural conversation flow. Practice speaking your answers out loud."
                accent="primary"
                delay={0}
              />
              <FeatureCard
                icon={MessageSquare}
                title="Chat With Your Notes"
                description="Not ready to talk? Chat with your documents instead. Ask questions, get explanations, and explore concepts at your own pace."
                accent="accent"
                delay={0.1}
              />
              <FeatureCard
                icon={FileText}
                title="Smart Document Ingestion"
                description="Drop any PDF or notes — we turn them into personalized exam questions in seconds. No manual setup required."
                accent="amber"
                delay={0.2}
              />
              <FeatureCard
                icon={Brain}
                title="Socratic Questioning"
                description="Don't just answer — explain. Our AI pushes you to truly understand, not just memorize. Build real comprehension."
                accent="emerald"
                delay={0.3}
              />
              <FeatureCard
                icon={Target}
                title="Adaptive Difficulty"
                description="Start easy, get harder as you improve. The AI meets you where you are and challenges you to grow."
                accent="primary"
                delay={0.4}
              />
              <FeatureCard
                icon={BarChart3}
                title="Deep Analytics"
                description="See exactly which concepts you've mastered and which need more work. Know where to focus your study time."
                accent="accent"
                delay={0.5}
              />
            </div>
          </div>
        </section>

        {/* How It Works Section */}
        <section id="how-it-works" className="py-32 relative bg-secondary/30">
          <div className="container mx-auto px-6">
            <motion.div
              className="text-center mb-20"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              <span className="text-primary font-medium mb-4 block">How It Works</span>
              <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-6">
                Three Simple Steps
              </h2>
            </motion.div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 lg:gap-12">
              {[
                {
                  step: "01",
                  title: "Upload Your Notes",
                  description: "Drop your PDFs, lecture notes, or textbook chapters. Our AI processes and understands the content in seconds.",
                  icon: FileText
                },
                {
                  step: "02",
                  title: "Start a Voice Exam",
                  description: "Choose between Exam mode for rigorous testing or Learn mode for guided exploration with hints allowed.",
                  icon: Mic
                },
                {
                  step: "03",
                  title: "Get Deep Insights",
                  description: "Receive comprehensive feedback and correction reports that identify exactly where to focus your studying.",
                  icon: GraduationCap
                }
              ].map((item, index) => (
                <motion.div
                  key={index}
                  className="relative"
                  initial={{ opacity: 0, y: 40 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: index * 0.15 }}
                >
                  <div className="flex flex-col items-center text-center">
                    <div className="relative mb-8">
                      <div className="absolute inset-0 bg-primary/30 blur-2xl" />
                      <div className="relative w-20 h-20 rounded-2xl bg-card border border-border/50 flex items-center justify-center">
                        <item.icon className="h-8 w-8 text-primary" />
                      </div>
                      <span className="absolute -top-3 -right-3 w-8 h-8 rounded-full bg-primary text-primary-foreground text-sm font-bold flex items-center justify-center">
                        {item.step}
                      </span>
                    </div>
                    <h3 className="text-2xl font-bold mb-4">{item.title}</h3>
                    <p className="text-muted-foreground leading-relaxed max-w-sm">{item.description}</p>
                  </div>
                  {index < 2 && (
                    <div className="hidden lg:block absolute top-10 left-[calc(100%+1rem)] w-[calc(100%-2rem)]">
                      <div className="w-full h-px bg-gradient-to-r from-border via-primary/50 to-border" />
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* Bloom's Taxonomy Section */}
        <section className="py-32 relative overflow-hidden">
          <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1/2 h-[600px]">
            <FloatingOrb size={400} color="primary" delay={0} />
            <FloatingOrb size={300} color="accent" delay={2} />
          </div>

          <div className="container mx-auto px-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
              <motion.div
                initial={{ opacity: 0, x: -40 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6 }}
              >
                <span className="text-primary font-medium mb-4 block">Pedagogy First</span>
                <h2 className="text-4xl md:text-5xl font-bold tracking-tight mb-6">
                  Built on Bloom&apos;s Taxonomy
                </h2>
                <p className="text-lg text-muted-foreground mb-10 leading-relaxed">
                  We don&apos;t just ask you to remember facts. Our AI dynamically adjusts
                  question complexity to traverse all six levels of cognitive learning,
                  ensuring comprehensive mastery.
                </p>

                <div className="space-y-4">
                  {[
                    { title: "Remember & Understand", desc: "Recall facts and explain basic concepts", color: "bg-blue-500" },
                    { title: "Apply & Analyze", desc: "Use information in new situations and draw connections", color: "bg-purple-500" },
                    { title: "Evaluate & Create", desc: "Justify decisions and produce original work", color: "bg-primary" }
                  ].map((item, i) => (
                    <motion.div
                      key={i}
                      className="flex items-start gap-4 p-5 rounded-2xl bg-card/50 border border-border/50 backdrop-blur-sm"
                      initial={{ opacity: 0, x: -20 }}
                      whileInView={{ opacity: 1, x: 0 }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.4, delay: i * 0.1 }}
                    >
                      <div className={`w-1.5 h-14 rounded-full ${item.color} shrink-0`} />
                      <div>
                        <h3 className="font-semibold text-lg mb-1">{item.title}</h3>
                        <p className="text-muted-foreground">{item.desc}</p>
                      </div>
                    </motion.div>
                  ))}
                </div>
              </motion.div>

              <motion.div
                className="relative"
                initial={{ opacity: 0, x: 40 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6 }}
              >
                <Card className="relative border-border/50 bg-card/80 backdrop-blur-xl shadow-2xl overflow-hidden">
                  <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-accent/5" />
                  <CardHeader className="relative">
                    <CardTitle className="flex items-center gap-3">
                      <Layers className="h-6 w-6 text-primary" />
                      Cognitive Assessment
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="relative space-y-6">
                    {[
                      { label: "Knowledge Retrieval", value: 95, color: "bg-blue-500" },
                      { label: "Critical Analysis", value: 88, color: "bg-purple-500" },
                      { label: "Creative Synthesis", value: 72, color: "bg-primary" }
                    ].map((item, i) => (
                      <div key={i} className="space-y-2">
                        <div className="flex justify-between text-sm font-medium">
                          <span>{item.label}</span>
                          <span className="text-muted-foreground">{item.value}%</span>
                        </div>
                        <div className="h-2 w-full rounded-full bg-secondary overflow-hidden">
                          <motion.div
                            className={`h-full ${item.color}`}
                            initial={{ width: 0 }}
                            whileInView={{ width: `${item.value}%` }}
                            viewport={{ once: true }}
                            transition={{ duration: 1, delay: i * 0.2 }}
                          />
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </Card>
              </motion.div>
            </div>
          </div>
        </section>

        {/* Who Is This For Section */}
        <section className="py-32 relative bg-secondary/30">
          <div className="container mx-auto px-6">
            <motion.div
              className="text-center mb-16"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              <span className="text-primary font-medium mb-4 block">Who Is This For</span>
              <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-6">
                Built For Students Who Want More
              </h2>
              <p className="max-w-2xl mx-auto text-lg text-muted-foreground">
                Whether you&apos;re preparing for board exams, competitive tests, or just want to
                master your coursework — VOXAM adapts to your subject and level.
              </p>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {[
                {
                  icon: Stethoscope,
                  title: "Medical Students",
                  description: "Practice viva voce for anatomy, physiology, and clinical rounds",
                  accent: "primary"
                },
                {
                  icon: Cpu,
                  title: "Engineering Students",
                  description: "Master conceptual subjects like thermodynamics, circuits, and mechanics",
                  accent: "accent"
                },
                {
                  icon: Scale,
                  title: "Law Students",
                  description: "Prepare for moot court and sharpen your case analysis skills",
                  accent: "amber"
                },
                {
                  icon: GraduationCap,
                  title: "High School Students",
                  description: "Get ahead of the curve. Experience the future of learning before everyone else.",
                  accent: "emerald"
                }
              ].map((item, index) => {
                const accentColors: Record<string, string> = {
                  primary: "from-primary/20 to-transparent",
                  accent: "from-accent/20 to-transparent",
                  amber: "from-amber-500/20 to-transparent",
                  emerald: "from-emerald-500/20 to-transparent"
                }
                const iconColors: Record<string, string> = {
                  primary: "text-primary",
                  accent: "text-accent",
                  amber: "text-amber-500",
                  emerald: "text-emerald-500"
                }
                return (
                  <motion.div
                    key={index}
                    initial={{ opacity: 0, y: 30 }}
                    whileInView={{ opacity: 1, y: 0 }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.5, delay: index * 0.1 }}
                  >
                    <Card className="relative overflow-hidden border-border/50 bg-card/50 backdrop-blur-sm h-full">
                      <div className={`absolute inset-0 bg-gradient-to-br ${accentColors[item.accent]}`} />
                      <CardHeader className="relative pb-2">
                        <div className={`mb-3 w-12 h-12 rounded-xl bg-secondary/80 flex items-center justify-center ${iconColors[item.accent]}`}>
                          <item.icon className="h-6 w-6" />
                        </div>
                        <CardTitle className="text-lg">{item.title}</CardTitle>
                      </CardHeader>
                      <CardContent className="relative">
                        <p className="text-sm text-muted-foreground">{item.description}</p>
                      </CardContent>
                    </Card>
                  </motion.div>
                )
              })}
            </div>
          </div>
        </section>

        {/* Platform Stats */}
        <section className="py-20 relative">
          <div className="container mx-auto px-6">
            <motion.div
              className="text-center"
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              <p className="text-xl md:text-2xl text-muted-foreground font-medium mb-8">
                Built by students who were tired of passive studying
              </p>
              <div className="flex flex-wrap justify-center gap-8 md:gap-16">
                <div className="text-center">
                  <div className="text-3xl md:text-4xl font-bold text-gradient mb-2">2 Modes</div>
                  <div className="text-sm text-muted-foreground">Voice Exams + Chat</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl md:text-4xl font-bold text-gradient mb-2">Any Subject</div>
                  <div className="text-sm text-muted-foreground">Works with your notes</div>
                </div>
                <div className="text-center">
                  <div className="text-3xl md:text-4xl font-bold text-gradient mb-2">Your Pace</div>
                  <div className="text-sm text-muted-foreground">Learn or Exam mode</div>
                </div>
              </div>
            </motion.div>
          </div>
        </section>

        {/* Pricing Section */}
        <section id="pricing" className="py-32 relative">
          <div className="container mx-auto px-6">
            <motion.div
              className="text-center mb-20"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              <span className="text-primary font-medium mb-4 block">Pricing</span>
              <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-6">
                Simple, Transparent
              </h2>
              <p className="max-w-xl mx-auto text-lg text-muted-foreground">
                Buy minutes once, use anytime. No subscriptions, no hidden fees.
              </p>
            </motion.div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
              <PricingCard
                title="Free Trial"
                price="₹0"
                description="Try before you buy"
                features={[
                  "15 mins voice exam",
                  "10 chat messages",
                  "1 document (20 pages)"
                ]}
                delay={0}
              />
              <PricingCard
                title="Starter"
                price="₹399"
                description="Perfect for getting started"
                features={[
                  "100 mins voice exams",
                  "500 chat messages",
                  "100 document pages",
                  "AI feedback reports"
                ]}
                delay={0.1}
              />
              <PricingCard
                title="Standard"
                price="₹699"
                description="Best value for most students"
                features={[
                  "200 mins voice exams",
                  "1,000 chat messages",
                  "250 document pages",
                  "AI feedback reports"
                ]}
                popular
                delay={0.2}
              />
              <PricingCard
                title="Achiever"
                price="₹1,299"
                description="For serious exam prep"
                features={[
                  "350 mins voice exams",
                  "1,500 chat messages",
                  "500 document pages",
                  "AI feedback reports"
                ]}
                delay={0.3}
              />
            </div>
          </div>
        </section>

        {/* FAQ Section */}
        <section id="faq" className="py-32 relative bg-secondary/30">
          <div className="container mx-auto px-6">
            <motion.div
              className="text-center mb-16"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              <span className="text-primary font-medium mb-4 block">FAQ</span>
              <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight">
                Common Questions
              </h2>
            </motion.div>

            <div className="max-w-3xl mx-auto space-y-4">
              {[
                {
                  question: "What subjects does VOXAM work with?",
                  answer: "Any subject you can upload notes for — medicine, engineering, law, sciences, humanities, and more. If you can study it, VOXAM can examine you on it."
                },
                {
                  question: "What document types are supported?",
                  answer: "We support PDF files and images (JPG, PNG). Upload lecture slides, textbook chapters, handwritten notes — if it's readable, we can process it."
                },
                {
                  question: "What if I don't want to talk?",
                  answer: "Use chat mode instead. Same AI, same depth — just text-based. Ask questions, get explanations, and explore concepts at your own pace."
                },
                {
                  question: "Is my data private?",
                  answer: "Yes. Your documents are encrypted and never shared or used for AI training. Your study materials remain yours."
                },
                {
                  question: "Can I use it on mobile?",
                  answer: "Yes, VOXAM works on any device with a browser and microphone. Study anywhere, anytime."
                }
              ].map((item, index) => (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.4, delay: index * 0.1 }}
                >
                  <details className="group">
                    <summary className="flex cursor-pointer items-center justify-between rounded-2xl bg-card/80 border border-border/50 p-6 transition-colors hover:border-primary/30">
                      <span className="font-semibold text-lg">{item.question}</span>
                      <ChevronDown className="h-5 w-5 text-muted-foreground transition-transform group-open:rotate-180" />
                    </summary>
                    <div className="px-6 py-4 text-muted-foreground leading-relaxed">
                      {item.answer}
                    </div>
                  </details>
                </motion.div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className="py-32 relative overflow-hidden">
          <div className="absolute inset-0">
            <div className="absolute inset-0 bg-gradient-to-br from-primary/20 via-background to-accent/10" />
            <FloatingOrb size={400} color="primary" delay={0} />
            <FloatingOrb size={300} color="accent" delay={2} />
          </div>

          <div className="container mx-auto px-6 relative">
            <motion.div
              className="max-w-3xl mx-auto text-center"
              initial={{ opacity: 0, y: 30 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6 }}
            >
              <h2 className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-tight mb-6">
                Stop Reading.
                <br />
                <span className="text-gradient">Start Understanding.</span>
              </h2>
              <p className="text-lg text-muted-foreground mb-10 leading-relaxed">
                Your first 15 minutes are free. No credit card required.
              </p>
              <Link href="/login">
                <Button size="lg" className="h-14 rounded-full px-10 text-base font-medium glow-blue">
                  Start Your Free Exam
                  <ArrowRight className="ml-2 h-5 w-5" />
                </Button>
              </Link>
            </motion.div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border/40 py-16">
        <div className="container mx-auto px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
            <div className="col-span-2 md:col-span-1">
              <Link href="/" className="flex items-center gap-3 mb-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
                  <Volume2 className="h-5 w-5" />
                </div>
                <span className="text-xl font-bold">VOXAM</span>
              </Link>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Revolutionizing education through conversational AI assessment.
              </p>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Product</h3>
              <ul className="space-y-3 text-sm text-muted-foreground">
                <li><a href="#features" className="hover:text-foreground transition-colors">Features</a></li>
                <li><a href="#pricing" className="hover:text-foreground transition-colors">Pricing</a></li>
                <li><a href="#how-it-works" className="hover:text-foreground transition-colors">How it Works</a></li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Company</h3>
              <ul className="space-y-3 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-foreground transition-colors">About</a></li>
                <li><a href="#" className="hover:text-foreground transition-colors">Blog</a></li>
                <li><a href="#" className="hover:text-foreground transition-colors">Careers</a></li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Legal</h3>
              <ul className="space-y-3 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-foreground transition-colors">Privacy</a></li>
                <li><a href="#" className="hover:text-foreground transition-colors">Terms</a></li>
              </ul>
            </div>
          </div>
          <div className="flex flex-col md:flex-row justify-between items-center pt-8 border-t border-border/40 text-sm text-muted-foreground">
            <p>© 2025 VOXAM. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
