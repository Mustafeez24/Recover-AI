import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AdvisoryBanner } from "@/components/AdvisoryBanner";
import { NavBar } from "@/components/NavBar";
import { QueryProvider } from "@/lib/query-provider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "RecoverAI",
  description: "AI-powered revenue recovery agent",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-zinc-50 dark:bg-black">
        <QueryProvider>
          <AdvisoryBanner />
          <NavBar />
          <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-8">{children}</main>
        </QueryProvider>
      </body>
    </html>
  );
}
