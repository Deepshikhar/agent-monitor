import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sploink — Agent Monitor",
  description: "Real-time AI agent telemetry and behavioral analysis",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">
        <nav className="border-b border-[#2d3148] bg-[#1a1d27] px-6 py-3 flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-md bg-indigo-600 flex items-center justify-center">
              <span className="text-white text-xs font-bold">S</span>
            </div>
            <span className="font-semibold text-white tracking-tight">Sploink</span>
          </div>
          <span className="text-[#2d3148]">|</span>
          <span className="text-sm text-[#94a3b8]">Agent Monitor</span>
          <div className="ml-auto flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-[#94a3b8]">Live</span>
          </div>
        </nav>
        <main className="p-6 max-w-7xl mx-auto">{children}</main>
      </body>
    </html>
  );
}
