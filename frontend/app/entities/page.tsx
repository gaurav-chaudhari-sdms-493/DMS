"use client";
import { useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Network,
  Loader2,
  AlertCircle,
  History,
  FileText,
  X,
  ShieldCheck,
  ShieldQuestion,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import RegionHighlightViewer from "@/components/drive/RegionHighlightViewer";

interface FieldProvenance {
  kind: "base" | "amendment";
  evidence_fact_id: string | null;
  amendment_id?: string | null;
  amendment_type?: string;
  effective_date?: string;
}

interface RecordView {
  record_id: string;
  record_type: string;
  current: { fields: Record<string, any>; legal_status: string; field_provenance: Record<string, FieldProvenance> };
  original: { fields: Record<string, any>; legal_status: string };
}

interface LinkedEntity {
  edge_id: string;
  edge_type: string;
  tier: number;
  status: string;
  confidence: number | null;
  direction: "outgoing" | "incoming";
  other_node: { id: string; entity_type: string; label: string };
}

interface LinkedFact {
  edge_id: string;
  edge_type: string;
  tier: number;
  status: string;
  confidence: number | null;
  fact: { fact_id: string; field_name: string; value: any; document_id: string; document_title: string | null };
}

interface Entity360 {
  node: { id: string; entity_type: string; label: string; attributes: Record<string, any> };
  records: RecordView[];
  linked_entities: LinkedEntity[];
  linked_facts: LinkedFact[];
}

interface RecordHistory {
  base: { fields: Record<string, any>; record_type: string; evidence_fact_id: string | null; created_at: string };
  amendments: {
    id: string;
    amendment_type: string;
    effective_date: string;
    field_changes: Record<string, any>;
    legal_status: string | null;
    evidence_fact_id: string;
  }[];
}

function formatValue(v: any): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

function EdgeStatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    machine: "bg-[#f0f4f9] text-[#444746]",
    held: "bg-amber-50 text-amber-700",
    verified: "bg-green-50 text-green-700",
  };
  const icon = status === "verified" ? <ShieldCheck className="w-3 h-3" /> : status === "held" ? <ShieldQuestion className="w-3 h-3" /> : null;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${styles[status] || "bg-[#f0f4f9] text-[#444746]"}`}>
      {icon}
      {status}
    </span>
  );
}

export default function Entity360Page() {
  const [nodeId, setNodeId] = useState("");
  const [data, setData] = useState<Entity360 | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [historyRecordId, setHistoryRecordId] = useState<string | null>(null);
  const [history, setHistory] = useState<RecordHistory | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  const [viewingFactId, setViewingFactId] = useState<string | null>(null);

  const load = async (id?: string) => {
    const target = (id ?? nodeId).trim();
    if (!target) {
      setError("Enter an entity node ID first.");
      return;
    }
    setNodeId(target);
    setLoading(true);
    setError("");
    setData(null);
    try {
      const result = await api.entities.get360(target);
      setData(result);
    } catch (e: any) {
      setError(e?.message || "Failed to load this entity");
    } finally {
      setLoading(false);
    }
  };

  const openHistory = async (recordId: string) => {
    setHistoryRecordId(recordId);
    setHistory(null);
    setHistoryLoading(true);
    try {
      const result = await api.records.getHistory(recordId);
      setHistory(result);
    } catch (e: any) {
      setError(e?.message || "Failed to load record history");
      setHistoryRecordId(null);
    } finally {
      setHistoryLoading(false);
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
            <Network className="w-5 h-5 text-[#0b57d0]" />
            Entity 360
          </h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-6">
        <Card className="bg-white border border-[#e1e3e1] mb-6">
          <div className="flex gap-2">
            <input
              type="text"
              aria-label="Entity node ID"
              placeholder="Entity node ID"
              value={nodeId}
              onChange={(e) => setNodeId(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && load()}
              className="flex-1 text-sm px-3 py-2 rounded-lg border border-[#e1e3e1] focus:outline-none focus:ring-2 focus:ring-[#0b57d0]/40"
            />
            <Button size="sm" loading={loading} onClick={() => load()}>
              Load
            </Button>
          </div>
        </Card>

        {error && (
          <div className="mb-6 flex items-center gap-2 px-4 py-2.5 rounded-xl bg-red-50 border border-red-200 text-sm text-red-700">
            <AlertCircle className="w-4 h-4 shrink-0" />
            {error}
          </div>
        )}

        {loading && (
          <div className="flex justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-[#0b57d0]" />
          </div>
        )}

        {data && (
          <div className="flex flex-col gap-6">
            <Card className="bg-white border border-[#e1e3e1]">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold">{data.node.label}</h2>
                  <p className="text-xs text-[#747775] uppercase tracking-wide mt-1">{data.node.entity_type}</p>
                </div>
              </div>
              {Object.keys(data.node.attributes || {}).length > 0 && (
                <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                  {Object.entries(data.node.attributes).map(([k, v]) => (
                    <div key={k}>
                      <span className="text-[#747775]">{k}: </span>
                      <span className="font-medium">{formatValue(v)}</span>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            <Card className="bg-white border border-[#e1e3e1]">
              <h3 className="text-sm font-bold mb-4">Records ({data.records.length})</h3>
              {data.records.length === 0 && <p className="text-sm text-[#747775]">No records for this entity.</p>}
              <div className="flex flex-col gap-4">
                {data.records.map((r) => (
                  <div key={r.record_id} className="border border-[#e1e3e1] rounded-xl p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div>
                        <span className="text-sm font-bold">{r.record_type}</span>
                        <span className="ml-2 text-xs text-[#747775]">status: {r.current.legal_status}</span>
                      </div>
                      <button
                        onClick={() => openHistory(r.record_id)}
                        className="flex items-center gap-1 text-xs font-bold text-[#0b57d0] hover:underline"
                      >
                        <History className="w-3.5 h-3.5" /> View history
                      </button>
                    </div>
                    <table className="w-full text-xs mt-2">
                      <tbody>
                        {Object.entries(r.current.fields).map(([field, value]) => {
                          const prov = r.current.field_provenance[field];
                          return (
                            <tr key={field} className="border-t border-[#f0f4f9]">
                              <td className="py-1.5 pr-3 text-[#747775] align-top w-1/3">{field}</td>
                              <td className="py-1.5 pr-3 font-medium align-top">{formatValue(value)}</td>
                              <td className="py-1.5 text-right align-top">
                                {prov?.evidence_fact_id && (
                                  <button
                                    onClick={() => setViewingFactId(prov.evidence_fact_id!)}
                                    className="text-[10px] font-bold text-[#0b57d0] hover:underline flex items-center gap-1 ml-auto"
                                  >
                                    <FileText className="w-3 h-3" /> source
                                  </button>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="bg-white border border-[#e1e3e1]">
              <h3 className="text-sm font-bold mb-4">Linked entities ({data.linked_entities.length})</h3>
              {data.linked_entities.length === 0 && <p className="text-sm text-[#747775]">No linked entities.</p>}
              <div className="flex flex-col gap-2">
                {data.linked_entities.map((e) => (
                  <div key={e.edge_id} className="flex items-center justify-between border border-[#e1e3e1] rounded-lg px-3 py-2 text-xs">
                    <div>
                      <span className="font-bold">{e.edge_type}</span>
                      <span className="ml-2 text-[#747775]">
                        {e.direction === "outgoing" ? "→" : "←"} {e.other_node.label} ({e.other_node.entity_type})
                      </span>
                      <span className="ml-2 text-[#747775]">tier {e.tier}{e.confidence != null ? ` · ${Math.round(e.confidence * 100)}%` : ""}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <EdgeStatusBadge status={e.status} />
                      <button onClick={() => load(e.other_node.id)} className="font-bold text-[#0b57d0] hover:underline">
                        View
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="bg-white border border-[#e1e3e1]">
              <h3 className="text-sm font-bold mb-4">Linked facts ({data.linked_facts.length})</h3>
              {data.linked_facts.length === 0 && <p className="text-sm text-[#747775]">No linked facts.</p>}
              <div className="flex flex-col gap-2">
                {data.linked_facts.map((e) => (
                  <div key={e.edge_id} className="flex items-center justify-between border border-[#e1e3e1] rounded-lg px-3 py-2 text-xs">
                    <div>
                      <span className="font-bold">{e.edge_type}</span>
                      <span className="ml-2 text-[#747775]">
                        {e.fact.field_name} = {formatValue(e.fact.value)} ({e.fact.document_title || "unknown source"})
                      </span>
                      <span className="ml-2 text-[#747775]">tier {e.tier}{e.confidence != null ? ` · ${Math.round(e.confidence * 100)}%` : ""}</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <EdgeStatusBadge status={e.status} />
                      <button
                        onClick={() => setViewingFactId(e.fact.fact_id)}
                        className="flex items-center gap-1 font-bold text-[#0b57d0] hover:underline"
                      >
                        <FileText className="w-3 h-3" /> source
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        )}

        {historyRecordId && (
          <div role="presentation" className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs" onClick={() => setHistoryRecordId(null)}>
            <div
              role="presentation"
              className="w-full max-w-2xl max-h-[80vh] overflow-y-auto bg-white border border-[#e1e3e1] rounded-3xl shadow-2xl text-[#1f1f1f]"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between px-6 pt-6 pb-3 sticky top-0 bg-white">
                <h3 className="text-lg font-bold">Record history</h3>
                <button onClick={() => setHistoryRecordId(null)} className="p-1.5 text-[#747775] hover:text-[#1f1f1f] rounded-full hover:bg-[#f0f4f9]">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <div className="px-6 pb-6">
                {historyLoading ? (
                  <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 animate-spin text-[#0b57d0]" /></div>
                ) : history ? (
                  <div className="flex flex-col gap-4">
                    <div className="border border-[#e1e3e1] rounded-xl p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-xs font-bold uppercase tracking-wide text-[#747775]">Base entry</span>
                        <span className="text-[10px] text-[#747775]">{history.base.created_at}</span>
                      </div>
                      <table className="w-full text-xs">
                        <tbody>
                          {Object.entries(history.base.fields).map(([field, value]) => (
                            <tr key={field} className="border-t border-[#f0f4f9]">
                              <td className="py-1.5 pr-3 text-[#747775] w-1/3">{field}</td>
                              <td className="py-1.5 font-medium">{formatValue(value)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {history.base.evidence_fact_id && (
                        <button
                          onClick={() => setViewingFactId(history.base.evidence_fact_id!)}
                          className="mt-2 text-[10px] font-bold text-[#0b57d0] hover:underline flex items-center gap-1"
                        >
                          <FileText className="w-3 h-3" /> source
                        </button>
                      )}
                    </div>

                    {history.amendments.length === 0 && (
                      <p className="text-sm text-[#747775] text-center">No amendments — this record hasn&apos;t changed since it was entered.</p>
                    )}
                    {history.amendments.map((a) => (
                      <div key={a.id} className="border border-amber-200 bg-amber-50/40 rounded-xl p-4">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-bold uppercase tracking-wide text-amber-700">{a.amendment_type}</span>
                          <span className="text-[10px] text-[#747775]">effective {a.effective_date}</span>
                        </div>
                        <table className="w-full text-xs">
                          <tbody>
                            {Object.entries(a.field_changes).map(([field, value]) => (
                              <tr key={field} className="border-t border-amber-100">
                                <td className="py-1.5 pr-3 text-[#747775] w-1/3">{field}</td>
                                <td className="py-1.5 font-medium">{formatValue(value)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                        {a.legal_status && <p className="text-xs mt-2">legal status → <span className="font-bold">{a.legal_status}</span></p>}
                        <button
                          onClick={() => setViewingFactId(a.evidence_fact_id)}
                          className="mt-2 text-[10px] font-bold text-[#0b57d0] hover:underline flex items-center gap-1"
                        >
                          <FileText className="w-3 h-3" /> source
                        </button>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        )}

        {viewingFactId && (
          <div role="presentation" className="fixed inset-0 z-[60] flex items-center justify-center p-4 bg-black/50 backdrop-blur-xs" onClick={() => setViewingFactId(null)}>
            <div
              role="presentation"
              className="w-full max-w-3xl max-h-[85vh] overflow-y-auto bg-white border border-[#e1e3e1] rounded-3xl shadow-2xl text-[#1f1f1f] p-6"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold">Source</h3>
                <button onClick={() => setViewingFactId(null)} className="p-1.5 text-[#747775] hover:text-[#1f1f1f] rounded-full hover:bg-[#f0f4f9]">
                  <X className="w-5 h-5" />
                </button>
              </div>
              <RegionHighlightViewer factId={viewingFactId} renderWidth={640} />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
