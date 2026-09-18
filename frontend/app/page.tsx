"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";

export default function HomePage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      if (user) {
        router.replace("/chat");
      } else {
        router.replace("/login");
      }
    }
  }, [user, loading, router]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-[#0c1317]">
      <div className="w-10 h-10 border-4 border-[#00a884]/20 border-t-[#00a884] rounded-full animate-spin mb-4" />
      <p className="text-sm text-[#8696a0]">Loading Private Chat...</p>
    </div>
  );
}
