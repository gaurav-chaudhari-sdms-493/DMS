"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ShieldCheck,
  Loader2,
  CheckCircle2,
  Lock,
  Unlock,
  AlertCircle,
  Keyboard,
  PenLine,
  Pencil,
  Undo2,
  Eye,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";

interface QueueFact {
  fact_id: string;
  document_id: string;
  field_name: string;
  value: any;
  confidence: number | null;
  is_handwritten: boolean;
  claimed_by_actor_id: string | null;
}

type Category = "low_confidence" | "handwritten" | "marginalia" | "join_mismatch";

const CATEGORY_TABS: { key: Category; label: string; available: boolean }[] = [
  { key: "low_confidence", label: "Low Confidence", available: true },
  { key: "handwritten", label: "Handwritten", available: true },
  // T30 — marginalia now has a real capture path (VLM extraction writes
  // "_marginalia"-sentinel Facts for handwritten notes outside any field).
  { key: "marginalia", label: "Marginalia", available: true },
  // T26 — spread-join wiring; the left/right layout convention it reads
  // is a best-effort guess, not modeled on a real scanned spread (no
  // reference corpus yet, T25 stays blocked on A1).
  { key: "join_mismatch", label: "Join Mismatches", available: true },
];

function formatValue(value: any): string {
  if (value && typeof value === "object" && "v" in value) return String(value.v);
  if (value && typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export default function WorkbenchPage() {
  const [category, setCategory] = useState<Category>("low_confidence");
  const [facts, setFacts] = useState<QueueFact[]>([]);
  const [total, setTotal] = useState(0);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const [bulkFolderId, setBulkFolderId] = useState("");
  const [bulkThreshold, setBulkThreshold] = useState("0.8");
  const [bulkPolicyVersion, setBulkPolicyVersion] = useState("");
  const [bulkLoading, setBulkLoading] = useState(false);
  const [bulkResult, setBulkResult] = useState<{ confirmed_count: number; batch_id: string } | null>(null);

  // T80 — bulk edit: select rows, preview the change, then apply. One
  // typed value replaces every selected row's value — the common case
  // this is for (the same OCR misread recurring across many rows).
  const [selectedFactIds, setSelectedFactIds] = useState<Set<string>>(new Set());
  const [editValue, setEditValue] = useState("");
  const [editLoading, setEditLoading] = useState(false);
  const [editPreview, setEditPreview] = useState<{ changed_count: number; total: number; rows: any[] } | null>(null);
  const [editResult, setEditResult] = useState<{ batch_id: string; changed_count: number } | null>(null);

  const toggleFactSelection = (factId: string) => {
    setSelectedFactIds((prev) => {
      const next = new Set(prev);
      if (next.has(factId)) next.delete(factId);
      else next.add(factId);
      return next;
    });
    setEditPreview(null);
    setEditResult(null);
  };

  const buildEdits = () => Array.from(selectedFactIds).map((fact_id) => ({ fact_id, new_value: { v: editValue } }));

  const previewBulkEdit = async () => {
    if (selectedFactIds.size === 0 || !editValue.trim()) return;
    setEditLoading(true);
    setError("");
    try {
      const result = await api.facts.bulkEdit(buildEdits(), true);
      setEditPreview(result);
    } catch (e: any) {
      setError(e?.message || "Failed to preview the bulk edit");
    } finally {
      setEditLoading(false);
    }
  };

  const applyBulkEdit = async () => {
    if (selectedFactIds.size === 0 || !editValue.trim()) return;
    setEditLoading(true);
    setError("");
    try {
      const result = await api.facts.bulkEdit(buildEdits(), false);
      setEditResult(result);
      setEditPreview(null);
      setSelectedFactIds(new Set());
      setEditValue("");
      await loadQueue(category);
    } catch (e: any) {
      setError(e?.message || "Bulk edit failed");
    } finally {
      setEditLoading(false);
    }
  };

  const undoBulkEdit = async () => {
    if (!editResult) return;
    setEditLoading(true);
    setError("");
    try {
      await api.facts.revertBulkEdit(editResult.batch_id);
      setNotice(`Reverted bulk edit batch ${editResult.batch_id.slice(0, 8)}…`);
      setEditResult(null);
      await loadQueue(category);
    } catch (e: any) {
      setError(e?.message || "Failed to revert the bulk edit");
    } finally {
      setEditLoading(false);
    }
  };

  const loadQueue = useCallback(async (cat: Category) => {
    setLoading(true);
    setError("");
    try {
      const data = await api.facts.getQueue(cat, 50, 0);
      setFacts(data.facts || []);
      setTotal(data.total || 0);
      setSelectedIndex(0);
    } catch (e: any) {
      setError(e?.message || "Failed to load the adjudication queue");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadQueue(category);
  }, [category, loadQueue]);

  const selected = facts[selectedIndex] || null;

  const doAction = async (action: "claim" | "release" | "confirm" | "mark_handwritten") => {
    if (!selected) return;
    setActionLoading(true);
    setError("");
    setNotice("");
    try {
      if (action === "claim") await api.facts.claim(selected.fact_id);
      if (action === "release") await api.facts.release(selected.fact_id);
      if (action === "confirm") {
        await api.facts.confirm(selected.fact_id);
        setNotice(`Confirmed "${selected.field_name}" — removed from queue.`);
      }
      if (action === "mark_handwritten") {
        await api.facts.markHandwritten(selected.fact_id);
        setNotice(`Marked "${selected.field_name}" as handwritten — moved to the Handwritten queue.`);
      }
      await loadQueue(category);
    } catch (e: any) {
      setError(e?.message || `Failed to ${action.replace("_", " ")} this fact`);
    } finally {
      setActionLoading(false);
    }
  };

  // T54 — keyboard-first navigation: ↑/↓ move the selection, 'c' claims,
  // 'r' releases, Enter or 'a' confirms the selected fact. Ignored while
  // a text input has focus so typing into the bulk-confirm form doesn't
  // fight with queue navigation.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") return;

      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, facts.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === "c" || e.key === "C") {
        doAction("claim");
      } else if (e.key === "r" || e.key === "R") {
        doAction("release");
      } else if (e.key === "Enter" || e.key === "a" || e.key === "A") {
        doAction("confirm");
      } else if (e.key === "h" || e.key === "H") {
        doAction("mark_handwritten");
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [facts, selectedIndex, category]);

  const submitBulkConfirm = async () => {
    if (!bulkFolderId.trim() || !bulkPolicyVersion.trim()) {
      setError("Bulk confirm needs a corpus folder ID and a policy version.");
      return;
    }
    setBulkLoading(true);
    setError("");
    setBulkResult(null);
    try {
      const result = await api.facts.bulkConfirm(bulkFolderId.trim(), parseFloat(bulkThreshold), bulkPolicyVersion.trim());
      setBulkResult(result);
      await loadQueue(category);
    } catch (e: any) {
      setError(e?.message || "Bulk confirm failed");
    } finally {
      setBulkLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#f8f9fa] text-[#1f1f1f]">
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
            <ShieldCheck className="w-5 h-5 text-[#0b57d0]" />
            Verification Workbench
          </h1>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-[#747775]">
          <Keyboard className="w-4 h-4" />
          <span>&uarr;/&darr; navigate &middot; C claim &middot; R release &middot; Enter/A confirm &middot; H mark handwritten</span>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-6 grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6">
        <div>
          <div className="flex gap-2 mb-4">
            {CATEGORY_TABS.map((tab) => (
              <button
                key={tab.key}
                disabled={!tab.available}
                onClick={() => tab.available && setCategory(tab.key as Category)}
                title={!tab.available ? "Not built yet — no data source exists for this category" : undefined}
                className={`px-3.5 py-1.5 rounded-full text-xs font-bold border transition-colors ${
                  category === tab.key
                    ? "bg-[#0b57d0] text-white border-[#0b57d0]"
                    : tab.available
                    ? "bg-white text-[#444746] border-[#e1e3e1] hover:border-[#0b57d0]"
                    : "bg-[#f0f4f9] text-[#9aa0a6] border-[#e1e3e1] cursor-not-allowed"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {error && (
            <div className="mb-4 flex items-center gap-2 px-4 py-2.5 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {error}
            </div>
          )}
          {notice && (
            <div className="mb-4 flex items-center gap-2 px-4 py-2.5 rounded-xl bg-green-50 border border-green-200 text-sm text-green-700">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              {notice}
            </div>
          )}

          <Card className="bg-white border border-[#e1e3e1] p-0 overflow-hidden">
            <div className="px-5 py-3 border-b border-[#e1e3e1] flex items-center justify-between">
              <span className="text-sm font-semibold text-[#1f1f1f]">Queue &mdash; {total} item{total === 1 ? "" : "s"}</span>
              {loading && <Loader2 className="w-4 h-4 animate-spin text-[#0b57d0]" />}
            </div>

            {!loading && facts.length === 0 && (
              <div className="px-5 py-10 text-center text-sm text-[#747775]">
                Nothing to review in this queue right now.
              </div>
            )}

            <div className="divide-y divide-[#e1e3e1]">
              {facts.map((fact, idx) => (
                <div
                  key={fact.fact_id}
                  className={`w-full flex items-center gap-3 px-5 py-3 transition-colors ${
                    idx === selectedIndex ? "bg-[#e8f0fe]" : "hover:bg-[#f8f9fa]"
                  }`}
                >
                  <input
                    type="checkbox"
                    checked={selectedFactIds.has(fact.fact_id)}
                    onChange={() => toggleFactSelection(fact.fact_id)}
                    onClick={(e) => e.stopPropagation()}
                    className="shrink-0 w-4 h-4 accent-[#0b57d0]"
                    title="Select for bulk edit"
                  />
                  <button onClick={() => setSelectedIndex(idx)} className="flex-1 min-w-0 text-left flex items-center justify-between gap-4">
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-[#1f1f1f] truncate">{fact.field_name}</div>
                      <div className="text-xs text-[#747775] truncate">{formatValue(fact.value)}</div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {fact.claimed_by_actor_id && <Lock className="w-3.5 h-3.5 text-[#9aa0a6]" />}
                      <span className="text-xs font-mono text-[#444746]">
                        {fact.confidence !== null ? fact.confidence.toFixed(2) : "—"}
                      </span>
                    </div>
                  </button>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <div className="space-y-6">
          <Card className="bg-white border border-[#e1e3e1]">
            <h2 className="text-sm font-bold text-[#1f1f1f] mb-3">Selected fact</h2>
            {!selected ? (
              <p className="text-sm text-[#747775]">Select an item from the queue.</p>
            ) : (
              <div className="space-y-3">
                <div>
                  <div className="text-xs text-[#747775] uppercase tracking-wide font-semibold">Field</div>
                  <div className="text-sm text-[#1f1f1f]">{selected.field_name}</div>
                </div>
                <div>
                  <div className="text-xs text-[#747775] uppercase tracking-wide font-semibold">Value</div>
                  <div className="text-sm text-[#1f1f1f] break-words">{formatValue(selected.value)}</div>
                </div>
                <div>
                  <div className="text-xs text-[#747775] uppercase tracking-wide font-semibold">Confidence</div>
                  <div className="text-sm text-[#1f1f1f] font-mono">{selected.confidence?.toFixed(3) ?? "—"}</div>
                </div>
                {selected.is_handwritten && (
                  <div className="text-xs font-bold text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-2.5 py-1.5">
                    Handwritten source — T55 rule: cannot be bulk-confirmed
                  </div>
                )}
                <div className="flex flex-wrap gap-2 pt-2">
                  <Button size="sm" variant="secondary" loading={actionLoading} onClick={() => doAction(selected.claimed_by_actor_id ? "release" : "claim")}>
                    {selected.claimed_by_actor_id ? <Unlock className="w-3.5 h-3.5 mr-1.5" /> : <Lock className="w-3.5 h-3.5 mr-1.5" />}
                    {selected.claimed_by_actor_id ? "Release" : "Claim"}
                  </Button>
                  <Button size="sm" loading={actionLoading} onClick={() => doAction("confirm")}>
                    <CheckCircle2 className="w-3.5 h-3.5 mr-1.5" />
                    Confirm
                  </Button>
                  {!selected.is_handwritten && (
                    <Button size="sm" variant="secondary" loading={actionLoading} onClick={() => doAction("mark_handwritten")}>
                      <PenLine className="w-3.5 h-3.5 mr-1.5" />
                      Mark Handwritten
                    </Button>
                  )}
                </div>
              </div>
            )}
          </Card>

          <Card className="bg-white border border-[#e1e3e1]">
            <h2 className="text-sm font-bold text-[#1f1f1f] mb-1">Bulk confirm (T54)</h2>
            <p className="text-xs text-[#747775] mb-3">
              Promotes every in-review fact above the threshold in one corpus. Requires the corpus to be
              calibrated first (T59) — handwritten facts are always excluded regardless of confidence.
            </p>
            <div className="space-y-2">
              <input
                type="text"
                placeholder="Corpus folder ID"
                value={bulkFolderId}
                onChange={(e) => setBulkFolderId(e.target.value)}
                className="w-full text-sm px-3 py-2 rounded-lg border border-[#e1e3e1] focus:outline-none focus:ring-2 focus:ring-[#0b57d0]/40"
              />
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                placeholder="Threshold (0-1)"
                value={bulkThreshold}
                onChange={(e) => setBulkThreshold(e.target.value)}
                className="w-full text-sm px-3 py-2 rounded-lg border border-[#e1e3e1] focus:outline-none focus:ring-2 focus:ring-[#0b57d0]/40"
              />
              <input
                type="text"
                placeholder="Policy version label"
                value={bulkPolicyVersion}
                onChange={(e) => setBulkPolicyVersion(e.target.value)}
                className="w-full text-sm px-3 py-2 rounded-lg border border-[#e1e3e1] focus:outline-none focus:ring-2 focus:ring-[#0b57d0]/40"
              />
              <Button size="sm" className="w-full" loading={bulkLoading} onClick={submitBulkConfirm}>
                Bulk Confirm
              </Button>
            </div>
            {bulkResult && (
              <div className="mt-3 text-xs text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
                Confirmed {bulkResult.confirmed_count} fact{bulkResult.confirmed_count === 1 ? "" : "s"} — batch {bulkResult.batch_id.slice(0, 8)}&hellip;
              </div>
            )}
          </Card>

          <Card className="bg-white border border-[#e1e3e1]">
            <h2 className="text-sm font-bold text-[#1f1f1f] mb-1">Bulk edit (T80)</h2>
            <p className="text-xs text-[#747775] mb-3">
              Check rows in the queue, type the corrected value, preview before applying. Never marks a
              value verified — every edited row lands in review, even if it was previously machine or verified.
            </p>
            <div className="space-y-2">
              <div className="text-xs font-semibold text-[#444746]">
                {selectedFactIds.size} row{selectedFactIds.size === 1 ? "" : "s"} selected
              </div>
              <input
                type="text"
                placeholder="Corrected value"
                value={editValue}
                onChange={(e) => { setEditValue(e.target.value); setEditPreview(null); }}
                disabled={selectedFactIds.size === 0}
                className="w-full text-sm px-3 py-2 rounded-lg border border-[#e1e3e1] focus:outline-none focus:ring-2 focus:ring-[#0b57d0]/40 disabled:opacity-50"
              />
              <div className="flex gap-2">
                <Button
                  size="sm" variant="secondary" className="flex-1"
                  loading={editLoading} disabled={selectedFactIds.size === 0 || !editValue.trim()}
                  onClick={previewBulkEdit}
                >
                  <Eye className="w-3.5 h-3.5 mr-1.5" />
                  Preview
                </Button>
                <Button
                  size="sm" className="flex-1"
                  loading={editLoading} disabled={!editPreview || editPreview.changed_count === 0}
                  onClick={applyBulkEdit}
                >
                  <Pencil className="w-3.5 h-3.5 mr-1.5" />
                  Apply
                </Button>
              </div>
            </div>

            {editPreview && (
              <div className="mt-3 text-xs bg-[#f0f4f9] border border-[#e1e3e1] rounded-lg px-3 py-2 space-y-1 max-h-40 overflow-y-auto">
                <div className="font-semibold text-[#444746]">
                  {editPreview.changed_count} of {editPreview.total} row{editPreview.total === 1 ? "" : "s"} will change
                </div>
                {editPreview.rows.filter((r: any) => r.changed).map((r: any) => (
                  <div key={r.fact_id} className="text-[#1f1f1f]">
                    {r.field_name}: {formatValue(r.previous_value)} &rarr; {formatValue(r.new_value)}
                  </div>
                ))}
              </div>
            )}

            {editResult && (
              <div className="mt-3 flex items-center justify-between gap-2 text-xs text-green-700 bg-green-50 border border-green-200 rounded-lg px-3 py-2">
                <span>
                  Edited {editResult.changed_count} fact{editResult.changed_count === 1 ? "" : "s"} — batch {editResult.batch_id.slice(0, 8)}&hellip;
                </span>
                <button onClick={undoBulkEdit} className="flex items-center gap-1 font-bold text-[#0b57d0] hover:underline shrink-0">
                  <Undo2 className="w-3.5 h-3.5" /> Undo
                </button>
              </div>
            )}
          </Card>
        </div>
      </main>
    </div>
  );
}
