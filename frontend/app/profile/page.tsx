"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  User,
  Mail,
  Calendar,
  ShieldCheck,
  FileText,
  Folder,
  HardDrive,
  LogOut,
  ArrowLeft,
  KeyRound,
  BarChart2,
  PieChart,
  Loader2,
  AlertCircle
} from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

interface FileTypeCount {
  extension: string;
  count: number;
  size_bytes: number;
}


interface UserProfile {
  user_id: string;
  full_name: string;
  email: string;
  role: string;
  tenant_id: string;
  tenant_name: string;
  created_at: string;
  total_files: number;
  total_folders: number;
  total_size_bytes: number;
  total_chunks: number;
  file_types_breakdown: FileTypeCount[];
}

export default function ProfilePage() {
  const router = useRouter();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedExt, setSelectedExt] = useState<string | null>(null);
  const [extDocs, setExtDocs] = useState<any[]>([]);
  const [loadingExtDocs, setLoadingExtDocs] = useState(false);
  const [showLogoutConfirm, setShowLogoutConfirm] = useState(false);

  useEffect(() => {
    fetchProfile();
  }, []);

  const handleSelectExtension = async (ext: string) => {
    const extClean = ext.toLowerCase().replace(".", "");
    setSelectedExt(extClean);
    setLoadingExtDocs(true);
    try {
      const allDocs = await api.documents.list({ is_trashed: false });
      const filtered = allDocs.filter((d: any) => {
        const dExt = (d.title.split(".").pop() || "").toLowerCase();
        return dExt === extClean;
      });
      setExtDocs(filtered);
    } catch (err) {
      console.error("Failed to load documents for extension:", err);
    } finally {
      setLoadingExtDocs(false);
    }
  };

  const fetchProfile = async () => {
    setLoading(true);
    setError("");
    try {
      const data = await api.auth.getProfile();
      setProfile(data);
    } catch (err: any) {
      setError(err.message || "Failed to load profile details");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    api.auth.logout();
  };

  const formatSize = (bytes: number): string => {
    if (!bytes || bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div className="min-h-screen bg-background text-textMain">
      {/* Header Bar */}
      <header className="h-16 px-6 flex items-center justify-between border-b border-borderDark/60 bg-surface/50 backdrop-blur-md sticky top-0 z-20">
        <div className="flex items-center gap-4">
          <Link
            href="/drive"
            className="flex items-center gap-2 text-sm text-textMuted hover:text-textMain transition-colors px-3 py-1.5 rounded-lg hover:bg-white/5"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Drive</span>
          </Link>
          <div className="h-4 w-px bg-borderDark/60" />
          <h1 className="text-lg font-bold text-textMain">User Profile & Analytics</h1>
        </div>

        <Button
          variant="secondary"
          size="sm"
          onClick={() => setShowLogoutConfirm(true)}
          className="text-red-400 border-red-500/20 hover:bg-red-500/10 hover:border-red-500/30"
        >
          <LogOut className="w-4 h-4 mr-2" />
          <span>Log Out</span>
        </Button>
      </header>

      <main className="max-w-6xl mx-auto p-6 md:p-8 space-y-8">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 gap-3">
            <Loader2 className="w-8 h-8 text-primary animate-spin" />
            <p className="text-sm text-textMuted">Loading user profile & analytics...</p>
          </div>
        ) : error ? (
          <Card className="p-6 bg-red-500/10 border-red-500/20 text-red-500 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <div>
              <p className="font-semibold">Error Loading Profile</p>
              <p className="text-sm opacity-90">{error}</p>
            </div>
            <Button size="sm" variant="secondary" onClick={fetchProfile} className="ml-auto">
              Retry
            </Button>
          </Card>
        ) : profile ? (
          <>
            {/* User Profile Banner Card */}
            <Card glow className="p-6 md:p-8 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-64 h-64 bg-primary/5 rounded-full blur-3xl pointer-events-none" />

              <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
                <div className="flex items-center gap-5">
                  <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary to-orange-600 text-white font-bold text-2xl flex items-center justify-center shadow-lg shadow-primary/20 shrink-0">
                    {profile.full_name
                      .split(" ")
                      .map((n) => n[0])
                      .join("")
                      .toUpperCase()
                      .slice(0, 2) || "U"}
                  </div>

                  <div className="space-y-1">
                    <div className="flex items-center gap-3 flex-wrap">
                      <h2 className="text-2xl font-bold text-textMain">{profile.full_name}</h2>
                      <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-primary/10 text-primary border border-primary/20">
                        {profile.role}
                      </span>
                    </div>

                    <div className="flex items-center gap-4 text-sm text-textMuted flex-wrap">
                      <span className="flex items-center gap-1.5">
                        <Mail className="w-4 h-4 text-textMuted" />
                        {profile.email}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <Calendar className="w-4 h-4 text-textMuted" />
                        Joined {profile.created_at}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-3 w-full md:w-auto">
                  <Link href="/forgot-password" className="w-full md:w-auto">
                    <Button variant="secondary" size="md" className="w-full">
                      <KeyRound className="w-4 h-4 mr-2 text-primary" />
                      <span>Change Password</span>
                    </Button>
                  </Link>
                </div>
              </div>
            </Card>

            {/* Analytics Overview Cards Grid */}
            <div className="space-y-4">
              <h3 className="text-lg font-bold text-textMain flex items-center gap-2">
                <BarChart2 className="w-5 h-5 text-primary" />
                <span>Live Drive Analytics</span>
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <Card className="p-5 border-borderDark/80 hover:border-primary/40 transition-colors">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-textMuted">Total Files</span>
                    <div className="p-2 rounded-xl bg-blue-500/10 text-blue-400">
                      <FileText className="w-5 h-5" />
                    </div>
                  </div>
                  <div className="mt-4">
                    <p className="text-3xl font-extrabold text-textMain">{profile.total_files.toLocaleString()}</p>
                    <p className="text-xs text-textMuted mt-1">Uploaded documents in vault</p>
                  </div>
                </Card>

                <Card className="p-5 border-borderDark/80 hover:border-primary/40 transition-colors">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-textMuted">Storage Used</span>
                    <div className="p-2 rounded-xl bg-orange-500/10 text-orange-400">
                      <HardDrive className="w-5 h-5" />
                    </div>
                  </div>
                  <div className="mt-4">
                    <p className="text-3xl font-extrabold text-textMain">{formatSize(profile.total_size_bytes)}</p>
                    <p className="text-xs text-textMuted mt-1">Total document storage occupied</p>
                  </div>
                </Card>

                <Card className="p-5 border-borderDark/80 hover:border-primary/40 transition-colors">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold uppercase tracking-wider text-textMuted">Folders</span>
                    <div className="p-2 rounded-xl bg-indigo-500/10 text-indigo-400">
                      <Folder className="w-5 h-5" />
                    </div>
                  </div>
                  <div className="mt-4">
                    <p className="text-3xl font-extrabold text-textMain">{profile.total_folders.toLocaleString()}</p>
                    <p className="text-xs text-textMuted mt-1">Organized directory folders</p>
                  </div>
                </Card>
              </div>
            </div>

            {/* Document Format Breakdown */}
            <Card className="p-6 md:p-8 space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-bold text-textMain flex items-center gap-2">
                  <PieChart className="w-5 h-5 text-primary" />
                  <span>File Formats Distribution</span>
                </h3>
                <span className="text-xs text-textMuted">Click any format to view all matching files</span>
              </div>

              {profile.file_types_breakdown && profile.file_types_breakdown.length > 0 ? (
                <div className="max-h-[360px] overflow-y-auto pr-2 space-y-4 custom-scrollbar">
                  {profile.file_types_breakdown.map((item, idx) => {
                    const pct = profile.total_files > 0 ? Math.round((item.count / profile.total_files) * 100) : 0;
                    const extUpper = (item.extension || "OTHER").toUpperCase();

                    const colorMap: Record<string, string> = {
                      PDF: "bg-red-500 text-red-400",
                      DOCX: "bg-blue-500 text-blue-400",
                      DOC: "bg-blue-400 text-blue-300",
                      XLSX: "bg-emerald-500 text-emerald-400",
                      XLS: "bg-emerald-400 text-emerald-300",
                      CSV: "bg-teal-500 text-teal-400",
                      PPTX: "bg-amber-500 text-amber-400",
                      PPT: "bg-amber-400 text-amber-300",
                      TXT: "bg-purple-500 text-purple-400",
                      JSON: "bg-cyan-500 text-cyan-400",
                      MD: "bg-indigo-500 text-indigo-400",
                      RTF: "bg-pink-500 text-pink-400",
                      PNG: "bg-sky-500 text-sky-400",
                      JPG: "bg-indigo-500 text-indigo-400",
                      JPEG: "bg-indigo-500 text-indigo-400",
                    };

                    const badgeColor = colorMap[extUpper] || "bg-gray-500 text-gray-400";
                    const bgColorClass = badgeColor.split(" ")[0];

                    return (
                      <div
                        key={idx}
                        onClick={() => handleSelectExtension(item.extension)}
                        className="space-y-1.5 p-2 rounded-xl hover:bg-surface/80 transition-all cursor-pointer group border border-transparent hover:border-primary/20"
                        title={`Click to view all .${item.extension} files`}
                      >
                        <div className="flex items-center justify-between text-sm">
                          <div className="flex items-center gap-2.5">
                            <span className={`px-2.5 py-0.5 rounded text-xs font-bold text-white shadow-xs group-hover:scale-105 transition-transform ${bgColorClass}`}>
                              {extUpper}
                            </span>
                            <span className="font-semibold text-textMain group-hover:text-primary transition-colors">{item.count} files</span>
                          </div>
                          <span className="text-xs text-textMuted font-mono">
                            {formatSize(item.size_bytes)} ({pct}%)
                          </span>
                        </div>
                        <div className="w-full bg-surface/80 rounded-full h-2 overflow-hidden border border-borderDark/40">
                          <div
                            className={`${bgColorClass} h-full rounded-full transition-all duration-500`}
                            style={{ width: `${Math.max(2, pct)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center py-8 text-textMuted text-sm">
                  No documents uploaded yet. Upload files to view extension analytics.
                </div>
              )}
            </Card>

            {/* Filtered Files Modal */}
            {selectedExt && (
              <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
                <Card glow className="p-6 max-w-2xl w-full space-y-4 max-h-[85vh] flex flex-col">
                  <div className="flex items-center justify-between border-b border-borderDark/60 pb-3">
                    <div className="flex items-center gap-2.5">
                      <div className="px-3 py-1 rounded-lg bg-primary/20 text-primary font-bold text-xs uppercase tracking-wider border border-primary/30">
                        .{selectedExt}
                      </div>
                      <h4 className="text-lg font-bold text-textMain">
                        All .{selectedExt.toUpperCase()} Files ({extDocs.length})
                      </h4>
                    </div>
                    <Button variant="secondary" size="sm" onClick={() => setSelectedExt(null)}>
                      Close
                    </Button>
                  </div>

                  <div className="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
                    {loadingExtDocs ? (
                      <div className="flex items-center justify-center py-12 gap-2 text-textMuted text-sm">
                        <Loader2 className="w-4 h-4 animate-spin text-primary" />
                        <span>Fetching .{selectedExt} documents...</span>
                      </div>
                    ) : extDocs.length === 0 ? (
                      <div className="text-center py-12 text-sm text-textMuted">
                        No .{selectedExt} documents found.
                      </div>
                    ) : (
                      extDocs.map((doc) => (
                        <div
                          key={doc.id}
                          className="p-3.5 rounded-xl bg-surface/50 border border-borderDark/60 hover:border-primary/40 flex items-center justify-between gap-4 transition-all"
                        >
                          <div className="flex items-center gap-3 min-w-0">
                            <FileText className="w-5 h-5 text-primary shrink-0" />
                            <div className="min-w-0">
                              <p className="font-semibold text-sm text-textMain truncate">{doc.title}</p>
                              <p className="text-xs text-textMuted">
                                {formatSize(doc.file_size_bytes || 0)} • Created {new Date(doc.created_at).toLocaleDateString()}
                              </p>
                            </div>
                          </div>

                          <Link
                            href="/drive"
                            className="px-3 py-1.5 bg-primary/10 hover:bg-primary/20 text-primary text-xs font-semibold rounded-lg border border-primary/20 transition-all shrink-0"
                          >
                            Open in Drive
                          </Link>
                        </div>
                      ))
                    )}
                  </div>
                </Card>
              </div>
            )}

            {/* Logout Modal Confirmation */}
            {showLogoutConfirm && (
              <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50 animate-fadeIn">
                <Card glow className="p-6 max-w-md w-full space-y-4">
                  <h4 className="text-lg font-bold text-textMain flex items-center gap-2">
                    <LogOut className="w-5 h-5 text-red-500" />
                    <span>Confirm Log Out</span>
                  </h4>
                  <p className="text-sm text-textMuted">
                    Are you sure you want to end your session? You will need to sign in again to access your drive.
                  </p>
                  <div className="flex items-center justify-end gap-3 pt-2">
                    <Button variant="secondary" size="md" onClick={() => setShowLogoutConfirm(false)}>
                      Cancel
                    </Button>
                    <Button variant="primary" size="md" onClick={handleLogout} className="bg-red-600 hover:bg-red-700">
                      Log Out
                    </Button>
                  </div>
                </Card>
              </div>
            )}
          </>
        ) : null}
      </main>
    </div>
  );
}
