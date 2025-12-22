

"use client"

import Link from 'next/link'
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  Mic,
  FileText,
  Brain,
  BarChart3,
  GraduationCap,
  Check,
  ArrowRight,
  Users,
  Shield,
  Sparkles,
  MessageSquare
} from "lucide-react"

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col bg-background font-sans text-foreground selection:bg-primary/20">
      {/* Sticky Header with Glassmorphism */}
      <header className="sticky top-0 z-50 w-full border-b border-border/40 bg-background/80 backdrop-blur-md supports-backdrop-filter:bg-background/60">
        <div className="container mx-auto flex h-16 items-center justify-between px-4 md:px-6">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <Mic className="h-5 w-5" />
            </div>
            <span className="text-lg font-bold tracking-tight">Voxam</span>
          </div>

          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-muted-foreground">
            <button onClick={() => document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' })} className="hover:text-foreground transition-colors">Features</button>
            <button onClick={() => document.getElementById('methodology')?.scrollIntoView({ behavior: 'smooth' })} className="hover:text-foreground transition-colors">Methodology</button>
            <button onClick={() => document.getElementById('pricing')?.scrollIntoView({ behavior: 'smooth' })} className="hover:text-foreground transition-colors">Pricing</button>
          </nav>

          <div className="flex items-center gap-4">
            <Link href="/login">
              <Button size="sm" className="rounded-full px-6">
                Get Started
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* Hero Section */}
        <section className="relative overflow-hidden pt-24 pb-32 md:pt-32 md:pb-48">
          <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,var(--tw-gradient-stops))] from-primary/20 via-background to-background opacity-40"></div>
          <div className="container mx-auto px-4 md:px-6 text-center">
            <Badge variant="secondary" className="mb-6 px-4 py-1.5 text-sm font-medium rounded-full border-primary/20 bg-primary/10 text-primary">
              <Sparkles className="mr-2 h-3.5 w-3.5" />
              Intelligent. Instant. Interactive.
            </Badge>

            <h1 className="mx-auto max-w-4xl text-5xl font-extrabold tracking-tight sm:text-6xl md:text-7xl lg:text-8xl">
              Master Your Subjects with <br className="hidden md:block" />
              <span className="bg-linear-to-r from-primary via-purple-500 to-blue-600 bg-clip-text text-transparent">
                AI Voice Exams
              </span>
            </h1>

            <p className="mx-auto mt-6 max-w-2xl text-lg text-muted-foreground md:text-xl leading-relaxed">
              Experience the future of assessment. Upload your notes, engage in real-time voice conversations, and get instant, deep pedagogical feedback.
            </p>

            <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link href="/login">
                <Button size="lg" className="h-12 rounded-full px-8 text-base shadow-lg shadow-primary/20 transition-all hover:scale-105">
                  Start Free Exam <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <Button variant="outline" size="lg" className="h-12 rounded-full px-8 text-base">
                View Demo
              </Button>
            </div>
          </div>
        </section>

        {/* Bento Grid Features Section */}
        <section id="features" className="py-24 bg-muted/30">
          <div className="container mx-auto px-4 md:px-6">
            <div className="mb-16 text-center">
              <h2 className="text-3xl font-bold tracking-tighter sm:text-4xl md:text-5xl">Advanced AI Features</h2>
              <p className="mt-4 text-muted-foreground md:text-lg max-w-2xl mx-auto">
                Everything you need to assess understanding, not just memorization.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 auto-rows-[minmax(200px,auto)]">
              {/* Large Card - Voice Interaction */}
              <Card className="md:col-span-2 md:row-span-2 overflow-hidden border-border/50 bg-background/50 backdrop-blur-sm hover:border-primary/50 transition-colors">
                <CardHeader>
                  <div className="mb-2 w-12 h-12 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-500">
                    <Mic className="h-6 w-6" />
                  </div>
                  <CardTitle className="text-2xl">Real-time Voice Interaction</CardTitle>
                  <CardDescription className="text-base">
                    Engage in natural, fluid conversations with our AI agents. Powered by WebRTC for sub-second latency, it feels like talking to a real professor.
                  </CardDescription>
                </CardHeader>
                <CardContent className="relative min-h-[200px] flex items-center justify-center p-0">
                  {/* Abstract visual representation of voice waves */}
                  <div className="absolute inset-0 bg-linear-to-t from-background to-transparent z-10"></div>
                  <div className="w-full h-full bg-[url('/images/voice-interaction.png')] bg-cover bg-center opacity-90"></div>
                </CardContent>
              </Card>

              {/* Card - Document Processing */}
              <Card className="border-border/50 bg-background/50 backdrop-blur-sm hover:border-primary/50 transition-colors">
                <CardHeader>
                  <div className="mb-2 w-10 h-10 rounded-lg bg-orange-500/10 flex items-center justify-center text-orange-500">
                    <FileText className="h-5 w-5" />
                  </div>
                  <CardTitle>Intelligent Ingestion</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    Upload PDFs, DOCX, or TXT files. Our AI extracts key concepts and generates relevant questions instantly.
                  </p>
                </CardContent>
              </Card>

              {/* Card - Analytics */}
              <Card className="border-border/50 bg-background/50 backdrop-blur-sm hover:border-primary/50 transition-colors">
                <CardHeader>
                  <div className="mb-2 w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center text-green-500">
                    <BarChart3 className="h-5 w-5" />
                  </div>
                  <CardTitle>Deep Analytics</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    Get detailed reports on your performance, highlighting strengths and areas for improvement.
                  </p>
                </CardContent>
              </Card>

              {/* Card - Socratic Method */}
              <Card className="md:col-span-3 border-border/50 bg-background/50 backdrop-blur-sm hover:border-primary/50 transition-colors">
                <CardHeader className="text-center md:text-left">
                  <div className="flex justify-center md:justify-start mb-2">
                    <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center text-purple-500">
                      <Brain className="h-5 w-5" />
                    </div>
                  </div>
                  <CardTitle>Socratic Questioning Engine</CardTitle>
                  <CardDescription className="mt-2">
                    Our AI probes deeper with &quot;Why?&quot; and &quot;How?&quot; questions, building critical thinking skills.
                  </CardDescription>
                  <div className="flex flex-wrap justify-center md:justify-start gap-2 pt-4">
                    <Badge variant="secondary">Critical Thinking</Badge>
                    <Badge variant="secondary">Analysis</Badge>
                    <Badge variant="secondary">Synthesis</Badge>
                  </div>
                </CardHeader>
              </Card>
            </div>
          </div>
        </section>

        {/* Bloom's Taxonomy Section */}
        <section id="methodology" className="py-24">
          <div className="container mx-auto px-4 md:px-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
              <div>
                <Badge variant="outline" className="mb-4 border-primary/50 text-primary">Pedagogy First</Badge>
                <h2 className="text-3xl font-bold tracking-tighter sm:text-4xl mb-6">
                  Built on Bloom&apos;s Taxonomy
                </h2>
                <p className="text-lg text-muted-foreground mb-8 leading-relaxed">
                  We don&apos;t just ask you to remember facts. Our AI dynamically adjusts question complexity to traverse all six levels of cognitive learning, ensuring a comprehensive assessment of your mastery.
                </p>

                <div className="space-y-4">
                  {[
                    { title: "Remember & Understand", desc: "Recall facts and explain basic concepts", color: "bg-blue-500" },
                    { title: "Apply & Analyze", desc: "Use information in new situations and draw connections", color: "bg-purple-500" },
                    { title: "Evaluate & Create", desc: "Justify a stand or decision and produce new or original work", color: "bg-pink-500" }
                  ].map((item, i) => (
                    <div key={i} className="flex items-start gap-4 p-4 rounded-xl border border-border/50 bg-muted/20">
                      <div className={`w-2 h-12 rounded-full ${item.color} shrink-0`} />
                      <div>
                        <h3 className="font-semibold text-lg">{item.title}</h3>
                        <p className="text-muted-foreground">{item.desc}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="relative">
                <div className="absolute inset-0 bg-linear-to-r from-blue-500 to-purple-600 blur-3xl opacity-20 rounded-full"></div>
                <Card className="relative border-border/50 bg-background/80 backdrop-blur-xl shadow-2xl">
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2">
                      <GraduationCap className="h-6 w-6 text-primary" />
                      Assessment Engine
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-6">
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm font-medium">
                        <span>Knowledge Retrieval</span>
                        <span className="text-muted-foreground">95%</span>
                      </div>
                      <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                        <div className="h-full bg-blue-500 w-[95%]" />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm font-medium">
                        <span>Critical Analysis</span>
                        <span className="text-muted-foreground">88%</span>
                      </div>
                      <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                        <div className="h-full bg-purple-500 w-[88%]" />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm font-medium">
                        <span>Creative Synthesis</span>
                        <span className="text-muted-foreground">72%</span>
                      </div>
                      <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
                        <div className="h-full bg-pink-500 w-[72%]" />
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        </section>

        {/* Pricing Section */}
        <section id="pricing" className="py-24 bg-muted/30">
          <div className="container mx-auto px-4 md:px-6">
            <div className="text-center mb-16">
              <h2 className="text-3xl font-bold tracking-tighter sm:text-4xl">Simple, Transparent Pricing</h2>
              <p className="mt-4 text-muted-foreground">Buy minutes once, use anytime. No subscriptions.</p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto">
              {/* Free Trial */}
              <Card className="border-border/50 bg-background/50 backdrop-blur-sm hover:shadow-lg transition-all text-center sm:text-left">
                <CardHeader>
                  <CardTitle>Free Trial</CardTitle>
                  <div className="mt-4 flex items-baseline justify-center sm:justify-start text-4xl font-extrabold tracking-tight">
                    ₹0
                  </div>
                  <CardDescription className="mt-2">Try before you buy</CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-3 text-sm">
                    <li className="flex items-center justify-center sm:justify-start"><Check className="mr-2 h-4 w-4 text-primary" /> 15 mins voice exam</li>
                    <li className="flex items-center justify-center sm:justify-start"><Check className="mr-2 h-4 w-4 text-primary" /> 10 chat messages</li>
                    <li className="flex items-center justify-center sm:justify-start"><Check className="mr-2 h-4 w-4 text-primary" /> 1 document (20 pages)</li>
                  </ul>
                  <Link href="/login" className="w-full">
                    <Button className="mt-8 w-full" variant="outline">Start Free</Button>
                  </Link>
                </CardContent>
              </Card>

              {/* Starter Pack */}
              <Card className="border-border/50 bg-background/50 backdrop-blur-sm hover:shadow-lg transition-all text-center sm:text-left">
                <CardHeader>
                  <CardTitle>Starter</CardTitle>
                  <div className="mt-4 flex items-baseline justify-center sm:justify-start text-4xl font-extrabold tracking-tight">
                    ₹299
                  </div>
                  <CardDescription className="mt-2">90 minutes of voice exams</CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-3 text-sm">
                    <li className="flex items-center justify-center sm:justify-start"><Check className="mr-2 h-4 w-4 text-primary" /> 90 mins voice exams</li>
                    <li className="flex items-center justify-center sm:justify-start"><Check className="mr-2 h-4 w-4 text-primary" /> Unlimited chat</li>
                    <li className="flex items-center justify-center sm:justify-start"><Check className="mr-2 h-4 w-4 text-primary" /> 50 document pages</li>
                    <li className="flex items-center justify-center sm:justify-start"><Check className="mr-2 h-4 w-4 text-primary" /> Correction reports</li>
                  </ul>
                  <Link href="/login" className="w-full">
                    <Button className="mt-8 w-full" variant="outline">Get Started</Button>
                  </Link>
                </CardContent>
              </Card>

              {/* Standard Pack - Most Popular */}
              <Card className="relative border-primary shadow-lg bg-background sm:scale-105 z-10 text-center sm:text-left">
                <div className="absolute -top-4 left-0 right-0 flex justify-center">
                  <Badge className="bg-primary hover:bg-primary">Most Popular</Badge>
                </div>
                <CardHeader>
                  <CardTitle>Standard</CardTitle>
                  <div className="mt-4 flex items-baseline justify-center sm:justify-start text-4xl font-extrabold tracking-tight">
                    ₹599
                  </div>
                  <CardDescription className="mt-2">250 minutes of voice exams</CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-3 text-sm">
                    <li className="flex items-center justify-center sm:justify-start"><Check className="mr-2 h-4 w-4 text-primary" /> 250 mins voice exams</li>
                    <li className="flex items-center justify-center sm:justify-start"><Check className="mr-2 h-4 w-4 text-primary" /> Unlimited chat</li>
                    <li className="flex items-center justify-center sm:justify-start"><Check className="mr-2 h-4 w-4 text-primary" /> 200 document pages</li>
                    <li className="flex items-center justify-center sm:justify-start"><Check className="mr-2 h-4 w-4 text-primary" /> Correction reports</li>
                  </ul>
                  <Link href="/login" className="w-full">
                    <Button className="mt-8 w-full">Get Started</Button>
                  </Link>
                </CardContent>
              </Card>

              {/* Achiever Pack */}
              <Card className="border-border/50 bg-background/50 backdrop-blur-sm hover:shadow-lg transition-all text-center sm:text-left">
                <CardHeader>
                  <CardTitle>Achiever</CardTitle>
                  <div className="mt-4 flex items-baseline justify-center sm:justify-start text-4xl font-extrabold tracking-tight">
                    ₹1,099
                  </div>
                  <CardDescription className="mt-2">500 minutes of voice exams</CardDescription>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-3 text-sm">
                    <li className="flex items-center justify-center sm:justify-start"><Check className="mr-2 h-4 w-4 text-primary" /> 500 mins voice exams</li>
                    <li className="flex items-center justify-center sm:justify-start"><Check className="mr-2 h-4 w-4 text-primary" /> Unlimited chat</li>
                    <li className="flex items-center justify-center sm:justify-start"><Check className="mr-2 h-4 w-4 text-primary" /> 500 document pages</li>
                    <li className="flex items-center justify-center sm:justify-start"><Check className="mr-2 h-4 w-4 text-primary" /> Correction reports</li>
                  </ul>
                  <Link href="/login" className="w-full">
                    <Button className="mt-8 w-full" variant="outline">Get Started</Button>
                  </Link>
                </CardContent>
              </Card>
            </div>

          </div>
        </section>

        {/* CTA Section */}
        <section className="py-24">
          <div className="container mx-auto px-4 md:px-6">
            <div className="relative rounded-3xl bg-primary px-6 py-16 md:px-16 md:py-24 overflow-hidden text-center">
              <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 mix-blend-soft-light"></div>
              <div className="relative z-10 max-w-3xl mx-auto">
                <h2 className="text-3xl font-bold tracking-tighter text-primary-foreground sm:text-4xl md:text-5xl">
                  Ready to transform your learning?
                </h2>
                <p className="mx-auto mt-6 max-w-xl text-lg text-primary-foreground/80">
                  Join thousands of students who are using AI to master complex subjects faster and more effectively.
                </p>
                <div className="mt-10 flex justify-center gap-4">
                  <Link href="/login">
                    <Button size="lg" variant="secondary" className="h-12 rounded-full px-8 text-base font-semibold">
                      Get Started Now
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border/40 bg-muted/20 py-12">
        <div className="container mx-auto px-4 md:px-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8 mb-12">
            <div className="col-span-2 md:col-span-1">
              <div className="flex items-center gap-2 mb-4">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                  <Mic className="h-5 w-5" />
                </div>
                <span className="text-lg font-bold">Voxam</span>
              </div>
              <p className="text-sm text-muted-foreground">
                Revolutionizing education through conversational AI assessment.
              </p>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Product</h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-foreground">Features</a></li>
                <li><a href="#" className="hover:text-foreground">Pricing</a></li>
                <li><a href="#" className="hover:text-foreground">Methodology</a></li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Company</h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-foreground">About</a></li>
                <li><a href="#" className="hover:text-foreground">Blog</a></li>
                <li><a href="#" className="hover:text-foreground">Careers</a></li>
              </ul>
            </div>
            <div>
              <h3 className="font-semibold mb-4">Legal</h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                <li><a href="#" className="hover:text-foreground">Privacy</a></li>
                <li><a href="#" className="hover:text-foreground">Terms</a></li>
              </ul>
            </div>
          </div>
          <div className="flex flex-col md:flex-row justify-between items-center pt-8 border-t border-border/40 text-sm text-muted-foreground">
            <p>© 2025 Voxam. All rights reserved.</p>
            <div className="flex gap-4 mt-4 md:mt-0">
              <a href="#" className="hover:text-foreground"><MessageSquare className="h-5 w-5" /></a>
              <a href="#" className="hover:text-foreground"><Users className="h-5 w-5" /></a>
              <a href="#" className="hover:text-foreground"><Shield className="h-5 w-5" /></a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
