import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
import { Toaster } from "@/components/ui/sonner";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "VOXAM - AI Voice Examination Platform for Students",
  description:
    "VOXAM is an AI-powered voice examination platform. Upload study materials, take voice-based exams with an AI tutor, and get instant feedback. Built for medical, engineering, law, and high school students.",
  keywords: [
    "AI exam",
    "voice learning",
    "study platform",
    "AI tutor",
    "exam preparation",
  ],
  authors: [{ name: "Vasanthan Arutselvan" }],
  openGraph: {
    title: "VOXAM - Learn by Speaking",
    description:
      "Stop re-reading notes. Start explaining them. AI-powered voice examinations.",
    url: "https://voxam.in",
    siteName: "VOXAM",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          forcedTheme="light"
          disableTransitionOnChange
        >
          {children}
          <Toaster position="bottom-right" richColors />
        </ThemeProvider>
      </body>
    </html>
  );
}
