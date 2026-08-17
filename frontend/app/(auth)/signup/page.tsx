"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Lock, Mail, User, AlertTriangle, ArrowRight, Eye, EyeOff } from "lucide-react";
import { api } from "@/lib/api";
import { storeTokens } from "@/lib/auth";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

export default function SignUpPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters long");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setLoading(true);

    try {
      const res = await api.auth.signUp(fullName, email, password);
      if (res.access_token && res.refresh_token) {
        storeTokens(res.access_token, res.refresh_token);
        router.push("/drive");
      } else {
        // Fallback login
        const loginRes = await api.auth.login(email, password);
        storeTokens(loginRes.access_token, loginRes.refresh_token);
        router.push("/drive");
      }
    } catch (err: any) {
      setError(err.message || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-8rem)] py-8">
      <div className="w-full max-w-md animate-fadeIn">
        <div className="text-center mb-8">
          <div className="flex justify-center mx-auto mb-6">
            <img src="/stark-drive.svg" alt="Stark Drive Logo" className="h-20 md:h-24 lg:h-28 w-auto object-contain drop-shadow-md" />
          </div>
          <h1 className="text-2xl font-bold text-textMain">Create Account</h1>
          <p className="text-textMuted mt-2">Get started with DocSearch AI document platform</p>
        </div>

        <Card glow className="p-8">
          <form onSubmit={handleSignUp} className="flex flex-col gap-4">
            {error && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-500 text-sm px-4 py-3 rounded-lg flex items-center gap-2 animate-[shake_0.5s_ease-in-out]">
                <AlertTriangle className="w-4 h-4 shrink-0" />
                {error}
              </div>
            )}

            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-textMuted group-focus-within:text-primary transition-colors">
                <User className="w-5 h-5" />
              </div>
              <input
                type="text"
                required
                placeholder="Full Name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full h-12 pl-10 pr-4 bg-surface/50 border border-borderDark rounded-lg text-textMain placeholder-textMuted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
              />
            </div>

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
                className="w-full h-12 pl-10 pr-4 bg-surface/50 border border-borderDark rounded-lg text-textMain placeholder-textMuted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
              />
            </div>

            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-textMuted group-focus-within:text-primary transition-colors">
                <Lock className="w-5 h-5" />
              </div>
              <input
                type={showPassword ? "text" : "password"}
                required
                placeholder="Password (min. 8 chars)"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full h-12 pl-10 pr-12 bg-surface/50 border border-borderDark rounded-lg text-textMain placeholder-textMuted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
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

            <div className="relative group">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-textMuted group-focus-within:text-primary transition-colors">
                <Lock className="w-5 h-5" />
              </div>
              <input
                type={showConfirmPassword ? "text" : "password"}
                required
                placeholder="Confirm Password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className="w-full h-12 pl-10 pr-12 bg-surface/50 border border-borderDark rounded-lg text-textMain placeholder-textMuted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
              />
              <button
                type="button"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-textMuted hover:text-textMain transition-colors focus:outline-none"
                title={showConfirmPassword ? "Hide password" : "Show password"}
              >
                {showConfirmPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>


            <Button type="submit" size="lg" className="w-full mt-2" loading={loading}>
              <span>Create Account</span>
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>

            <div className="text-center mt-4 text-sm text-textMuted">
              Already have an account?{" "}
              <Link href="/login" className="font-semibold text-primary hover:underline transition-all">
                Sign In
              </Link>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}
