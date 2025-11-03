"use client";
import { toast } from "sonner";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Button } from "./ui/button";
import Link from "next/link";
import { signIn, signUp } from "@/lib/auth-client";
import { useState } from "react";
import { useRouter } from "next/navigation";

const RegisterForm = () => {
  const [isPending, setIspending] = useState(false);
  const router = useRouter();

  const handleSubmit = async (evt: React.FormEvent<HTMLFormElement>) => {
    evt.preventDefault();
    const formData = new FormData(evt.target as HTMLFormElement);
    const name = String(formData.get("name"));
    if (!name) return toast.error("Please enter your name");

    const email = String(formData.get("email"));
    if (!email) return toast.error("Please enter your email");

    const password = String(formData.get("password"));
    if (!password) return toast.error("Please enter your password");

    await signUp.email(
      {
        name,
        email,
        password,
      },
      {
        onRequest: () => setIspending(true),
        onResponse: () => setIspending(false),
        onError: (ctx) => { toast.error(ctx.error.message); },
        onSuccess: () => router.push("/profile"),
      }
    );
  };

  return (
    <div className="max-w-sm w-full mx-auto mt-10 space-y-6 border rounded-xl shadow-md px-8 py-6 bg-white dark:bg-zinc-950">
      
      <div className="space-y-1 text-center mb-2">
        <h1 className="text-3xl font-bold">Let’s get started</h1>
        <p className="text-muted-foreground text-base">Create your account</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="name">Name</Label>
          <Input id="name" name="name" autoComplete="name" />
        </div>
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input id="email" name="email" autoComplete="email" />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input type="password" id="password" name="password" autoComplete="new-password" />
        </div>
        <Button type="submit" className="w-full" disabled={isPending}>
          Register
        </Button>
      </form>

     
      <div className="flex items-center gap-3 text-muted-foreground my-4">
        <div className="h-px bg-gray-300 flex-1" />
        <span className="text-sm font-medium">Or continue with</span>
        <div className="h-px bg-gray-300 flex-1" />
      </div>

      
      <Button
        variant="outline"
        className="w-full flex items-center justify-center gap-2  bg-black text-white"
        onClick={async () => {
          await signIn.social({ provider: "google" });
        }}
        disabled={isPending}
      >
        <svg
          className="h-5 w-5"
          viewBox="0 0 48 48"
          fill="none"
          aria-hidden="true"
        >
          <g>
            <path
              d="M44.5 20H24v8.5h11.7C34.2 32.1 29.7 35 24 35c-6.1 0-11.1-5-11.1-11.1S17.9 12.8 24 12.8c2.7 0 5.1 0.9 7 2.4l6.2-6.2C33.9 5.7 29.2 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20c11 0 19.7-8 19.7-19.6 0-1.3-.1-2.5-.2-3.4z"
              fill="#FFC107"
            />
            <path
              d="M6.3 14.7l7 5.1C15.7 16.7 19.5 14 24 14c2.7 0 5.1 0.9 7 2.4l6.2-6.2C33.9 5.7 29.2 4 24 4 16.3 4 9.3 8.9 6.3 14.7z"
              fill="#FF3D00"
            />
            <path
              d="M24 44c5.5 0 10.2-1.8 13.6-4.8l-6.3-5.1c-2.1 1.4-4.7 2.2-7.3 2.2-5.6 0-10.3-3.8-12-9l-7.2 5.5C7.8 39 15.3 44 24 44z"
              fill="#4CAF50"
            />
            <path
              d="M44.5 20H24v8.5h11.7c-1.4 3.8-5.3 6.5-11.7 6.5-6.1 0-11.1-5-11.1-11.1S17.9 12.8 24 12.8c2.7 0 5.1 0.9 7 2.4l6.2-6.2C33.9 5.7 29.2 4 24 4c-7.7 0-14.7 5.9-17.7 14.7z"
              fill="none"
            />
          </g>
        </svg>
        Continue with Google
      </Button>

      
      <p className="text-center text-sm text-muted-foreground mt-6">
        Already have an account?{" "}
        <Link
          href="/signin"
          className="font-semibold text-indigo-600 hover:underline"
        >
          Sign in here
        </Link>
      </p>
    </div>
  );
};

export default RegisterForm;
