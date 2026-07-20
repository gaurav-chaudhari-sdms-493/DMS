"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Zap, Search as SearchIcon, FileText } from "lucide-react";
import { isAuthenticated } from "@/lib/auth";
import { Button } from "@/components/ui/Button";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    if (isAuthenticated()) {
      router.replace("/search");
    }
  }, [router]);

  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-8rem)] text-center py-20 animate-fadeIn relative">
      {/* Background decoration */}
      <div className="absolute inset-0 z-[-1] overflow-hidden pointer-events-none flex justify-center items-center">
         <div className="w-[800px] h-[800px] bg-gradient-to-tr from-primary/10 via-transparent to-secondary/10 rounded-full blur-3xl opacity-50 animate-[pulseGlow_8s_infinite]"></div>
      </div>

      <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-6 leading-tight">
        <span className="text-textMain">AI-Powered</span> <br />
        <span className="gradient-text">Document Intelligence</span>
      </h1>
      
      <p className="text-lg md:text-xl text-textMuted max-w-2xl mb-10 leading-relaxed">
        Upload your documents and let our AI find answers, extract summaries, and connect the dots instantly. Stop searching, start knowing.
      </p>

      <div className="flex items-center gap-4 mb-20">
        <Link href="/login">
          <Button size="lg" className="w-40 text-lg group">
            Get Started
            <Zap className="w-5 h-5 ml-2 group-hover:text-yellow-400 transition-colors" />
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-5xl">
        <div className="glass p-8 rounded-2xl hover:-translate-y-2 transition-transform duration-300 border border-borderDark hover:border-primary/50 relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="w-12 h-12 rounded-xl bg-primary/20 text-primary flex items-center justify-center mb-6 shadow-[0_0_15px_rgba(99,102,241,0.2)]">
             <FileText className="w-6 h-6" />
          </div>
          <h3 className="text-xl font-bold text-textMain mb-3 text-left">Instant Upload</h3>
          <p className="text-textMuted text-left leading-relaxed text-sm">
            Securely upload PDFs, Word docs, and text files. Our system processes and indexes them in seconds.
          </p>
        </div>

        <div className="glass p-8 rounded-2xl hover:-translate-y-2 transition-transform duration-300 border border-borderDark hover:border-secondary/50 relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-secondary/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="w-12 h-12 rounded-xl bg-secondary/20 text-secondary flex items-center justify-center mb-6 shadow-[0_0_15px_rgba(6,182,212,0.2)]">
             <SearchIcon className="w-6 h-6" />
          </div>
          <h3 className="text-xl font-bold text-textMain mb-3 text-left">Semantic Search</h3>
          <p className="text-textMuted text-left leading-relaxed text-sm">
            Search by meaning, not just keywords. Our vector engine understands the context of your queries.
          </p>
        </div>

        <div className="glass p-8 rounded-2xl hover:-translate-y-2 transition-transform duration-300 border border-borderDark hover:border-success/50 relative overflow-hidden group">
          <div className="absolute inset-0 bg-gradient-to-br from-success/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
          <div className="w-12 h-12 rounded-xl bg-success/20 text-success flex items-center justify-center mb-6 shadow-[0_0_15px_rgba(16,185,129,0.2)]">
             <Zap className="w-6 h-6" />
          </div>
          <h3 className="text-xl font-bold text-textMain mb-3 text-left">AI Summaries</h3>
          <p className="text-textMuted text-left leading-relaxed text-sm">
            Get instant AI-generated answers synthesized from your documents, complete with source citations.
          </p>
        </div>
      </div>
    </div>
  );
}
