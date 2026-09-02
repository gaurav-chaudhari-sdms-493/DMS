"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  BarChart3,
  Loader2,
  AlertCircle,
  FileWarning,
  ListChecks,
  CheckCircle2,
  X,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import type { FolderTreeNode } from "@/types";

function flattenFolders(nodes: FolderTreeNode[], depth = 0): { id: string; name: string; depth: number }[] {
  const out: { id: string; name: string; depth: number }[] = [];
  for (const n of nodes) {
    out.push({ id: n.id, name: n.name, depth });
    const kids = n.subfolders || n.children || [];
    if (kids.length) out.push(...flattenFolders(kids, depth + 1));
  }
  return out;
}

interface Completeness {
  corpus_folder_id: string;
  documents: { total: number; pages_total: number; pages_failed: number; documents_with_failed_pages: number };
  data_loss: { documents_with_loss: number; total_missing_words: number };
  page_furniture: { documents_with_candidates: number };
  facts: { machine: number; in_review: number; verified: number; confidence_histogram: { bucket: string; count: number }[] };
  entity_edges: { machine: number; held: number; verified: number };
  missing_fields: { count: number };
}

const ROOT_FOLDER_ID = "root";

const DRILL_CATEGORIES: { key: string; label: string }[] = [
  { key: "missing_fields", label: "Missing required fields" },
  { key: "failed_pages", label: "Documents with failed pages" },
  { key: "unverified_facts", label: "Unverified facts (machine + in-review)" },
  { key: "machine_facts", label: "Auto-committed facts (machine only)" },
  { key: "data_loss_documents", label: "Documents with OCR data loss" },
  { key: "page_furniture_documents", label: "Documents with header/footer candidates" },
];

function StatBar({ label, value, total, color }: { label: string; value: number; total: number; color: string }) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div className="mb-2">
      <div className="flex justify-between text-xs mb-1">
        <span className="text-[#444746]">{label}</span>
        <span className="font-mono text-[#1f1f1f]">{value} ({pct}%)</span>
      </div>
      <div className="h-2 rounded-full bg-[#f0f4f9] overflow-hidden">
        <div className={`h-full ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function CompletenessDashboardPage() {
  const [folderId, setFolderId] = useState("");
  const [data, setData] = useState<Completeness | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [drillCategory, setDrillCategory] = useState<string | null>(null);
  const [drillRows, setDrillRows] = useState<any[] | null>(null);
  const [drillLoading, setDrillLoading] = useState(false);

  const [folders, setFolders] = useState<{ id: string; name: string; depth: number }[] | null>(null);
  const [foldersLoading, setFoldersLoading] = useState(false);
  const [showFolderPicker, setShowFolderPicker] = useState(false);

  const openFolderPicker = async () => {
    setShowFolderPicker((v) => !v);
    if (folders) return;
    setFoldersLoading(true);
    try {
      const tree = await api.folders.getTree();
      setFolders(flattenFolders(tree));
    } catch (e: any) {
      setError(e?.message || "Failed to load folders");
    } finally {
      setFoldersLoading(false);
    }
  };

  const loadDashboard = async (id?: string) => {
    const target = (id ?? folderId).trim();
    if (!target) {
      setError("Enter a corpus folder ID first.");
      return;
    }
    setFolderId(target);
    setShowFolderPicker(false);
    setLoading(true);
    setError("");
    setData(null);
    setDrillCategory(null);
    setDrillRows(null);
    try {
      const result = await api.governance.getCompleteness(target);
      setData(result);
    } catch (e: any) {
      setError(e?.message || "Failed to load the completeness dashboard for this corpus");
    } finally {
      setLoading(false);
    }
  };

  // Real documents are frequently unfiled (folder_id IS NULL) rather than
  // organized into folders, so a blank dashboard on first load -- with no
  // indication that "Root" is where the real data actually lives -- read
  // as broken ("failing on real folders") when a user instead pasted or
  // browsed to a folder that only had old, pre-page-tracking documents in
  // it. Auto-loading Root on mount gives a real, non-empty view by
  // default; Browse/Load still work exactly as before for any other folder.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {
    loadDashboard(ROOT_FOLDER_ID);
  }, []);

  const openDrill = async (category: string) => {
    setDrillCategory(category);
    setDrillRows(null);
    setDrillLoading(true);
    try {
      const rows = await api.governance.getCompletenessDrill(folderId.trim(), category);
      setDrillRows(rows);
    } catch (e: any) {
      setError(e?.message || "Failed to load drill-through");
      setDrillCategory(null);
    } finally {
      setDrillLoading(false);
    }
  };

  const factTotal = data ? data.facts.machine + data.facts.in_review + data.facts.verified : 0;
  const histogramMax = data ? Math.max(1, ...data.facts.confidence_histogram.map((b) => b.count)) : 1;

  return (
    <div className="h-screen overflow-y-auto bg-[#f8f9fa] text-[#1f1f1f]">
      <header className="h-16 px-6 flex items-center justify-between border-b border-[#e1e3e1]/60 bg-white/80 backdrop-blur-md sticky top-0 z-20">
        <div className="flex items-center gap-4">
          <Link
            href="/drive"
            className="flex items-center gap-2 text-sm text-[#444746] hover:text-[#1f1f1f] transition-colors px-3 py-1.5 rounded-lg hover:bg-[#f0f4f9]"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Drive</span>
          </Link>
          <div className="h-5 w-px bg-[#e1e3e1]" />
          <h1 className="text-lg font-bold text-[#1f1f1f] flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-[#0d2e5c]" />
            Completeness Dashboard
          </h1>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-6">
        <Card className="bg-white border border-[#e1e3e1] mb-6">
          <p className="text-[11px] text-[#747775] mb-2">
            Don&apos;t have a folder ID? Click <b>Browse folders</b> to pick a folder by name instead.
          </p>
          <div className="flex gap-2">
            <input
              type="text"
              aria-label="Corpus folder ID"
              placeholder="Click Browse folders to pick one — or paste a folder ID here"
              value={folderId}
              onChange={(e) => setFolderId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && loadDashboard()}
              className="flex-1 text-sm px-3 py-2 rounded-lg border border-[#e1e3e1] focus:outline-none focus:ring-2 focus:ring-[#0d2e5c]/40"
            />
            <Button variant="secondary" size="sm" loading={foldersLoading} onClick={openFolderPicker}>
              Browse folders
            </Button>
            <Button size="sm" loading={loading} onClick={() => loadDashboard()}>
              Load
            </Button>
          </div>
          {showFolderPicker && folders && (
            <div className="mt-3 max-h-64 overflow-y-auto flex flex-col gap-1">
              <button
                onClick={() => loadDashboard(ROOT_FOLDER_ID)}
                className="text-left text-sm py-1.5 px-3 rounded-lg hover:bg-[#f0f4f9] italic text-[#444746]"
              >
                Root — documents not in any folder
              </button>
              {folders.length === 0 && <p className="text-sm text-[#747775]">No sub-folders found.</p>}
              {folders.map((f) => (
                <button
                  key={f.id}
                  onClick={() => loadDashboard(f.id)}
                  style={{ paddingLeft: `${12 + f.depth * 16}px` }}
                  className="text-left text-sm py-1.5 pr-3 rounded-lg hover:bg-[#f0f4f9]"
                >
                  {f.name}
                </button>
              ))}
            </div>
          )}
        </Card>

        {error && (
          <div className="mb-6 flex items-center gap-2 px-4 py-2.5 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        {loading && (
          <div className="flex justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-[#0d2e5c]" />
          </div>
        )}

        {data && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="bg-white border border-[#e1e3e1]">
              <h2 className="text-sm font-bold mb-3">Documents</h2>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div><div className="text-2xl font-bold">{data.documents.total}</div><div className="text-xs text-[#747775]">total documents</div></div>
                <div><div className="text-2xl font-bold">{data.documents.pages_total}</div><div className="text-xs text-[#747775]">total pages</div></div>
                <div>
                  <div className={`text-2xl font-bold ${data.documents.pages_failed > 0 ? "text-amber-600" : ""}`}>{data.documents.pages_failed}</div>
                  <div className="text-xs text-[#747775]">failed pages</div>
                </div>
                <div>
                  <div className={`text-2xl font-bold ${data.documents.documents_with_failed_pages > 0 ? "text-amber-600" : ""}`}>{data.documents.documents_with_failed_pages}</div>
                  <div className="text-xs text-[#747775]">docs w/ failures</div>
                </div>
              </div>
              {data.documents.pages_failed > 0 && (
                <button
                  onClick={() => openDrill("failed_pages")}
                  className="mt-3 text-xs font-bold text-[#0d2e5c] hover:underline flex items-center gap-1"
                >
                  <FileWarning className="w-3.5 h-3.5" /> Drill into failed pages
                </button>
              )}
              {data.documents.total > 0 && data.documents.pages_total === 0 && (
                <p className="mt-3 text-xs text-[#747775] bg-[#f8f9fa] border border-[#e1e3e1] rounded-lg px-3 py-2">
                  This folder has {data.documents.total} document{data.documents.total === 1 ? "" : "s"}, but none
                  have a recorded page count — usually older documents uploaded before page-level tracking
                  existed. Try a different folder, or <b>Root</b> for unfiled documents, to see real stats.
                </p>
              )}
            </Card>

            <Card className="bg-white border border-[#e1e3e1]">
              <h2 className="text-sm font-bold mb-3">Missing required fields</h2>
              <div className={`text-3xl font-bold ${data.missing_fields.count > 0 ? "text-amber-600" : "text-green-600"}`}>
                {data.missing_fields.count}
              </div>
              <div className="text-xs text-[#747775] mb-3">gaps across classified documents</div>
              {data.missing_fields.count > 0 ? (
                <button
                  onClick={() => openDrill("missing_fields")}
                  className="text-xs font-bold text-[#0d2e5c] hover:underline flex items-center gap-1"
                >
                  <ListChecks className="w-3.5 h-3.5" /> Drill into missing fields
                </button>
              ) : (
                <div className="text-xs text-green-700 flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" /> No gaps found</div>
              )}
            </Card>

            <Card className="bg-white border border-[#e1e3e1]">
              <h2 className="text-sm font-bold mb-3">OCR data loss</h2>
              <div className={`text-3xl font-bold ${data.data_loss.documents_with_loss > 0 ? "text-amber-600" : "text-green-600"}`}>
                {data.data_loss.documents_with_loss}
              </div>
              <div className="text-xs text-[#747775] mb-3">
                documents where extracted text dropped words ({data.data_loss.total_missing_words} words missing total)
              </div>
              {data.data_loss.documents_with_loss > 0 ? (
                <button
                  onClick={() => openDrill("data_loss_documents")}
                  className="text-xs font-bold text-[#0d2e5c] hover:underline flex items-center gap-1"
                >
                  <FileWarning className="w-3.5 h-3.5" /> Drill into data loss
                </button>
              ) : (
                <div className="text-xs text-green-700 flex items-center gap-1"><CheckCircle2 className="w-3.5 h-3.5" /> No data loss detected</div>
              )}
            </Card>

            <Card className="bg-white border border-[#e1e3e1]">
              <h2 className="text-sm font-bold mb-3">Page furniture</h2>
              <div className="text-3xl font-bold">{data.page_furniture.documents_with_candidates}</div>
              <div className="text-xs text-[#747775] mb-3">documents with detected running headers/footers (informational, not an error)</div>
              {data.page_furniture.documents_with_candidates > 0 && (
                <button
                  onClick={() => openDrill("page_furniture_documents")}
                  className="text-xs font-bold text-[#0d2e5c] hover:underline flex items-center gap-1"
                >
                  <ListChecks className="w-3.5 h-3.5" /> Drill into page furniture
                </button>
              )}
            </Card>

            <Card className="bg-white border border-[#e1e3e1] md:col-span-2">
              <h2 className="text-sm font-bold mb-3">Facts — machine vs. verified split</h2>
              <StatBar label="Machine (auto-committed)" value={data.facts.machine} total={factTotal} color="bg-[#9aa0a6]" />
              <StatBar label="In review" value={data.facts.in_review} total={factTotal} color="bg-amber-500" />
              <StatBar label="Verified" value={data.facts.verified} total={factTotal} color="bg-green-500" />
              <div className="flex gap-3 mt-3">
                <button onClick={() => openDrill("machine_facts")} className="text-xs font-bold text-[#0d2e5c] hover:underline">
                  Drill into machine facts
                </button>
                <button onClick={() => openDrill("unverified_facts")} className="text-xs font-bold text-[#0d2e5c] hover:underline">
                  Drill into unverified (machine + in-review)
                </button>
              </div>
            </Card>

            <Card className="bg-white border border-[#e1e3e1] md:col-span-2">
              <h2 className="text-sm font-bold mb-3">Confidence distribution</h2>
              <div className="flex items-end gap-3 h-32">
                {data.facts.confidence_histogram.map((b) => (
                  <div key={b.bucket} className="flex-1 flex flex-col items-center justify-end h-full">
                    <div className="text-xs font-mono mb-1">{b.count}</div>
                    <div
                      className="w-full bg-[#0d2e5c]/70 rounded-t"
                      style={{ height: `${Math.max(4, (b.count / histogramMax) * 100)}%` }}
                    />
                    <div className="text-[10px] text-[#747775] mt-1">{b.bucket}</div>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="bg-white border border-[#e1e3e1] md:col-span-2">
              <h2 className="text-sm font-bold mb-3">Entity edges</h2>
              <div className="grid grid-cols-3 gap-3 text-sm">
                <div><div className="text-2xl font-bold">{data.entity_edges.machine}</div><div className="text-xs text-[#747775]">machine</div></div>
                <div><div className="text-2xl font-bold">{data.entity_edges.held}</div><div className="text-xs text-[#747775]">held (escrowed)</div></div>
                <div><div className="text-2xl font-bold">{data.entity_edges.verified}</div><div className="text-xs text-[#747775]">verified</div></div>
              </div>
            </Card>
          </div>
        )}

        {drillCategory && (
          <div role="presentation" className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs" onClick={() => setDrillCategory(null)}>
            <div
              role="presentation"
              className="w-full max-w-2xl max-h-[80vh] overflow-y-auto bg-white border border-[#e1e3e1] rounded-3xl shadow-2xl text-[#1f1f1f]"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between px-6 pt-6 pb-3 sticky top-0 bg-white">
                <h3 className="text-lg font-bold">{DRILL_CATEGORIES.find((c) => c.key === drillCategory)?.label}</h3>
                <button onClick={() => setDrillCategory(null)} className="p-1.5 text-[#747775] hover:text-[#1f1f1f] rounded-full hover:bg-[#f0f4f9]">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="px-6 pb-6">
                {drillLoading ? (
                  <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 animate-spin text-[#0d2e5c]" /></div>
                ) : drillRows && drillRows.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="text-left text-[#747775] border-b border-[#e1e3e1]">
                          {Object.keys(drillRows[0]).map((k) => (
                            <th key={k} className="py-2 pr-4 font-semibold">{k}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {drillRows.map((row, idx) => (
                          <tr key={idx} className="border-b border-[#f0f4f9]">
                            {Object.values(row).map((v, i) => (
                              <td key={i} className="py-2 pr-4 text-[#1f1f1f] font-mono">{String(v)}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="text-sm text-[#747775] py-8 text-center">Nothing in this category.</p>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
