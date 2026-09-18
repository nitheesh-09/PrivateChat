"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { ApiError } from "@/lib/api";
import { Lock, User, AlertCircle, ArrowRight, ShieldCheck } from "lucide-react";

export default function RegisterPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { user, register } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (user) {
      router.replace("/chat");
    }
  }, [user, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmedUser = username.trim();
    if (!trimmedUser || trimmedUser.length < 3) {
      setError("Username must be at least 3 characters.");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    try {
      await register(trimmedUser, password);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Registration failed. Please check your connection.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0c1317] flex flex-col items-center justify-center p-4 selection:bg-[#00a884]/30">
      {/* Brand Header Banner */}
      <div className="w-full max-w-md mb-8 flex flex-col items-center text-center">
        <div className="w-14 h-14 rounded-2xl bg-[#00a884]/15 border border-[#00a884]/30 flex items-center justify-center mb-3 text-[#00a884] shadow-lg shadow-[#00a884]/5">
          <ShieldCheck className="w-8 h-8" />
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-[#e9edef]">Private Chat</h1>
        <p className="text-xs text-[#8696a0] mt-1">Direct &amp; Group Messaging</p>
      </div>

      {/* Registration Card */}
      <div className="w-full max-w-md bg-[#111b21] border border-[#222e35] rounded-2xl p-6 sm:p-8 shadow-2xl shadow-black/50">
        <div className="mb-6 pb-4 border-b border-[#222e35]">
          <h2 className="text-xl font-bold text-[#e9edef]">Create Account</h2>
          <p className="text-xs text-[#8696a0] mt-1">Enter a username and password to register</p>
        </div>

        {error && (
          <div className="mb-5 p-3.5 bg-red-500/10 border border-red-500/30 rounded-xl text-xs text-red-400 flex items-start gap-2.5">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-[#8696a0] mb-1.5 uppercase tracking-wider">
              Username
            </label>
            <div className="relative flex items-center">
              <User className="absolute left-3.5 w-4 h-4 text-[#8696a0]" />
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
                autoComplete="username"
                required
                className="w-full bg-[#202c33] border border-[#2a3942] focus:border-[#00a884] focus:ring-1 focus:ring-[#00a884] rounded-xl pl-10 pr-4 py-2.5 text-sm text-[#e9edef] placeholder-[#8696a0] outline-none transition-all"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#8696a0] mb-1.5 uppercase tracking-wider">
              Password
            </label>
            <div className="relative flex items-center">
              <Lock className="absolute left-3.5 w-4 h-4 text-[#8696a0]" />
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter password"
                autoComplete="new-password"
                required
                className="w-full bg-[#202c33] border border-[#2a3942] focus:border-[#00a884] focus:ring-1 focus:ring-[#00a884] rounded-xl pl-10 pr-4 py-2.5 text-sm text-[#e9edef] placeholder-[#8696a0] outline-none transition-all"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#8696a0] mb-1.5 uppercase tracking-wider">
              Confirm Password
            </label>
            <div className="relative flex items-center">
              <Lock className="absolute left-3.5 w-4 h-4 text-[#8696a0]" />
              <input
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Confirm password"
                autoComplete="new-password"
                required
                className="w-full bg-[#202c33] border border-[#2a3942] focus:border-[#00a884] focus:ring-1 focus:ring-[#00a884] rounded-xl pl-10 pr-4 py-2.5 text-sm text-[#e9edef] placeholder-[#8696a0] outline-none transition-all"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full mt-2 bg-[#00a884] hover:bg-[#02be94] active:scale-[0.99] text-[#111b21] font-semibold py-2.5 px-4 rounded-xl text-sm transition-all duration-150 flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed shadow-md shadow-[#00a884]/10"
          >
            {isSubmitting ? (
              <div className="w-5 h-5 border-2 border-[#111b21]/30 border-t-[#111b21] rounded-full animate-spin" />
            ) : (
              <>
                <span>Create Account</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="mt-6 pt-5 border-t border-[#222e35] text-center">
          <p className="text-sm text-[#8696a0]">
            Already have an account?{" "}
            <Link
              href="/login"
              className="text-[#00a884] hover:text-[#02be94] font-semibold underline underline-offset-4 transition-colors ml-1"
            >
              Login
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
