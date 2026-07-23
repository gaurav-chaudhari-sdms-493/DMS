"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Lock, Mail, AlertTriangle, Eye, EyeOff } from "lucide-react";
import { api } from "@/lib/api";
import { storeTokens } from "@/lib/auth";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const res = await api.auth.login(email, password);
      storeTokens(res.access_token, res.refresh_token);
      router.push("/drive");
    } catch (err: any) {
      setError(err.message || "Invalid credentials");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-8rem)]">
      <div className="w-full max-w-md animate-fadeIn">
        <div className="text-center mb-8">
          <div className="bg-[#1e1e24] px-5 py-3 rounded-2xl mx-auto mb-4 shadow-[0_0_30px_rgba(253,82,0,0.3)] border border-primary/30 inline-flex items-center justify-center">
            <img src="/stark-logo-white.avif" alt="Stark Logo" className="h-9 w-auto object-contain" />
          </div>
          <h1 className="text-2xl font-bold text-textMain">Welcome Back</h1>
          <p className="text-textMuted mt-2">Sign in to your DocSearch AI account</p>
        </div>

        <Card glow className="p-8">
          <form onSubmit={handleLogin} className="flex flex-col gap-5">
            {error && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-500 text-sm px-4 py-3 rounded-lg flex items-center gap-2 animate-[shake_0.5s_ease-in-out]">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                {error}
              </div>
            )}

            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-textMuted group-focus-within:text-primary transition-colors">
                <Mail className="w-5 h-5" />
              </div>
              <input
                type="email"
                required
                placeholder="Email Address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full h-12 pl-10 pr-4 bg-surface/50 border border-borderDark rounded-lg text-textMain placeholder-textMuted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all peer"
              />
            </div>

            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-textMuted group-focus-within:text-primary transition-colors">
                <Lock className="w-5 h-5" />
              </div>
              <input
                type={showPassword ? "text" : "password"}
                required
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full h-12 pl-10 pr-12 bg-surface/50 border border-borderDark rounded-lg text-textMain placeholder-textMuted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all peer"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-textMuted hover:text-textMain transition-colors focus:outline-none"
                title={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>


            <div className="flex items-center justify-between mt-2">
              <label className="flex items-center gap-2 text-sm text-textMuted cursor-pointer hover:text-textMain transition-colors">
                <input type="checkbox" className="rounded border-borderDark bg-surface text-primary focus:ring-primary focus:ring-offset-background" />
                Remember me
              </label>
              <Link href="/forgot-password" className="text-sm font-medium text-primary hover:text-indigo-400 transition-colors">
                Forgot password?
              </Link>
            </div>

            <Button type="submit" size="lg" className="w-full mt-4" loading={loading}>
              Sign In
            </Button>

            <div className="text-center mt-4 text-sm text-textMuted">
              Don't have an account?{" "}
              <Link href="/signup" className="font-semibold text-primary hover:underline transition-all">
                Sign Up
              </Link>
            </div>

          </form>
        </Card>
      </div>
    </div>
  );
}
