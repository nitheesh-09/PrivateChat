import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/hooks/useAuth";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Private Chat | Secure 1-to-1 Messaging",
  description: "Private, real-time 1-to-1 messaging web application",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.className} bg-[#0c1317] text-[#e9edef] antialiased min-h-screen overflow-hidden`}>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
