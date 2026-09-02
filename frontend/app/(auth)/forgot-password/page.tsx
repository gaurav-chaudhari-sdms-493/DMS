"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Mail, Lock, Key, AlertTriangle, CheckCircle2, ArrowLeft, ArrowRight, Eye, EyeOff } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { useI18n } from "@/lib/i18n";
import { LanguageSwitcher } from "@/components/common/LanguageSwitcher";

export default function ForgotPasswordPage() {
  const router = useRouter();
  const { t } = useI18n();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [email, setEmail] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [infoMessage, setInfoMessage] = useState("");


  const handleRequestToken = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await api.auth.forgotPassword(email);
      setInfoMessage(res.message);
      setStep(2);
    } catch (err: any) {
      setError(err.message || "Failed to process request. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (newPassword.length < 8) {
      setError("New password must be at least 8 characters long");
      return;
    }

    if (newPassword !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    setLoading(true);

    try {
      await api.auth.resetPassword(email, resetToken, newPassword);
      setStep(3);
    } catch (err: any) {
      setError(err.message || "Failed to reset password. Token may be invalid or expired.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-8rem)] py-8">
      <div className="w-full max-w-md animate-fadeIn">
        <div className="flex justify-end mb-2">
          <LanguageSwitcher />
        </div>
        <div className="text-center mb-8">
          <div className="flex justify-center mx-auto mb-6">
            <img src="/stark-drive.svg" alt="Stark Drive Logo" className="h-20 md:h-24 lg:h-28 w-auto object-contain drop-shadow-md" />
          </div>
          <h1 className="text-2xl font-bold text-textMain">{t("auth.forgot.title", "Reset your password")}</h1>
          <p className="text-textMuted mt-2">
            {step === 1 && "Enter your email to request password reset code"}
            {step === 2 && "Enter reset token and your new password"}
            {step === 3 && "Your password has been successfully reset!"}
          </p>
        </div>

        <Card glow className="p-8">
          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-500 text-sm px-4 py-3 rounded-lg flex items-center gap-2 mb-4 animate-[shake_0.5s_ease-in-out]">
              <AlertTriangle className="w-4 h-4 shrink-0" />
              {error}
            </div>
          )}

          {step === 1 && (
            <form onSubmit={handleRequestToken} className="flex flex-col gap-4">
              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-textMuted group-focus-within:text-primary transition-colors">
                  <Mail className="w-5 h-5" />
                </div>
                <input
                  type="email"
                  required
                  aria-label={t("auth.forgot.email_label", "Email")}
                  placeholder={t("auth.forgot.email_label", "Email")}
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full h-12 pl-10 pr-4 bg-surface/50 border border-borderDark rounded-lg text-textMain placeholder-textMuted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                />
              </div>

              <Button type="submit" size="lg" className="w-full mt-2" loading={loading}>
                <span>{t("auth.forgot.submit", "Send reset link")}</span>
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>

              <div className="text-center mt-4">
                <Link href="/login" className="inline-flex items-center text-sm text-textMuted hover:text-textMain transition-colors">
                  <ArrowLeft className="w-4 h-4 mr-1.5" />
                  {t("auth.forgot.back_to_login", "Back to sign in")}
                </Link>
              </div>
            </form>
          )}

          {step === 2 && (
            <form onSubmit={handleResetPassword} className="flex flex-col gap-4">
              {infoMessage && (
                <div className="bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs px-3.5 py-2.5 rounded-lg mb-1">
                  {infoMessage}
                </div>
              )}

              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-textMuted group-focus-within:text-primary transition-colors">
                  <Key className="w-5 h-5" />
                </div>
                <input
                  type="text"
                  required
                  aria-label="Reset Code / Token"
                  placeholder="Reset Code / Token"
                  value={resetToken}
                  onChange={(e) => setResetToken(e.target.value)}
                  className="w-full h-12 pl-10 pr-4 bg-surface/50 border border-borderDark rounded-lg text-textMain placeholder-textMuted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all text-xs font-mono"
                />
              </div>

              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-textMuted group-focus-within:text-primary transition-colors">
                  <Lock className="w-5 h-5" />
                </div>
                <input
                  type={showNewPassword ? "text" : "password"}
                  required
                  aria-label="New Password (minimum 8 characters)"
                  placeholder="New Password (min. 8 chars)"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full h-12 pl-10 pr-12 bg-surface/50 border border-borderDark rounded-lg text-textMain placeholder-textMuted focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword(!showNewPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-textMuted hover:text-textMain transition-colors focus:outline-none"
                  title={showNewPassword ? "Hide password" : "Show password"}
                >
                  {showNewPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>

              <div className="relative group">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-textMuted group-focus-within:text-primary transition-colors">
                  <Lock className="w-5 h-5" />
                </div>
                <input
                  type={showConfirmPassword ? "text" : "password"}
                  required
                  aria-label="Confirm New Password"
                  placeholder="Confirm New Password"
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
                <span>Reset Password</span>
                <CheckCircle2 className="w-4 h-4 ml-2" />
              </Button>

              <div className="text-center mt-2">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="text-xs text-textMuted hover:text-primary transition-colors"
                >
                  Change Email Address
                </button>
              </div>
            </form>
          )}

          {step === 3 && (
            <div className="text-center py-4 space-y-6">
              <div className="w-14 h-14 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-full flex items-center justify-center mx-auto">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <p className="text-sm text-textMuted">
                Your password has been updated. You can now sign in using your new credentials.
              </p>
              <Button onClick={() => router.push("/login")} size="lg" className="w-full">
                Sign In Now
              </Button>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
