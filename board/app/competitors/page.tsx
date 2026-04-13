"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { useBrand } from "@/lib/brand-context";

type Competitor = {
  id: string;
  brand_id: string;
  name: string;
  slug: string;
  market: string | null;
  website: string | null;
  facebook_page_id: string | null;
  trustpilot_url: string | null;
  status: "active" | "watching" | "excluded";
  notes: string | null;
  last_analyzed_at: string | null;
  created_at: string;
};

type CompetitorAnalysis = {
  id: string;
  competitor_id: string;
  summary_json: any;
  report_md: string | null;
  ads_count: number;
  top_winners: any;
  created_at: string;
};

const STATUS_LABELS: Record<string, { label: string; className: string }> = {
  active: { label: "Aktiv", className: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" },
  watching: { label: "Gemerkt", className: "bg-amber-500/15 text-amber-400 border-amber-500/30" },
  excluded: { label: "Ausgeschlossen", className: "bg-red-500/15 text-red-400 border-red-500/30" },
};

function fmtDate(iso: string | null) {
  if (!iso) return "nie";
  const d = new Date(iso);
  const now = Date.now();
  const diff = now - d.getTime();
  const days = Math.floor(diff / 86400000);
  if (days === 0) return "heute";
  if (days === 1) return "gestern";
  if (days < 30) return `vor ${days} Tagen`;
  return d.toLocaleDateString("de-CH");
}

export default function CompetitorsPage() {
  const { brandId, loading: brandLoading } = useBrand();
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [latestByCompetitor, setLatestByCompetitor] = useState<
    Map<string, CompetitorAnalysis>
  >(new Map());
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Competitor | null>(null);

  useEffect(() => {
    if (!brandId) return;
    load(brandId);
  }, [brandId]);

  async function load(bid: string) {
    setLoading(true);
    const compRes = await supabase
      .from("competitors")
      .select("*")
      .eq("brand_id", bid)
      .order("status")
      .order("name");
    if (compRes.error || !compRes.data) {
      setLoading(false);
      return;
    }
    setCompetitors(compRes.data);

    const ids = compRes.data.map((c) => c.id);
    if (ids.length > 0) {
      const analysesRes = await supabase
        .from("competitor_analyses")
        .select("*")
        .in("competitor_id", ids)
        .order("created_at", { ascending: false });

      const map = new Map<string, CompetitorAnalysis>();
      for (const a of analysesRes.data ?? []) {
        if (!map.has(a.competitor_id)) map.set(a.competitor_id, a);
      }
      setLatestByCompetitor(map);
    }
    setLoading(false);
  }

  if (brandLoading || loading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted">
        Laden...
      </div>
    );
  }

  if (!brandId) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-muted">
        <p className="text-lg font-medium">Keine Brand konfiguriert</p>
      </div>
    );
  }

  if (competitors.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-80 text-muted p-6">
        <p className="text-lg font-semibold text-foreground">
          Noch keine Competitors
        </p>
        <p className="text-sm mt-2 max-w-md text-center">
          Führe{" "}
          <code className="bg-background px-1.5 py-0.5 rounded text-xs">
            python3 scripts/sync_to_board.py
          </code>{" "}
          im Creative-Generator-Ordner aus, um die bestehenden Competitors aus{" "}
          <code className="bg-background px-1.5 py-0.5 rounded text-xs">
            competitors.json
          </code>{" "}
          zu synchronisieren.
        </p>
      </div>
    );
  }

  const grouped = new Map<string, Competitor[]>();
  for (const c of competitors) {
    const list = grouped.get(c.status) ?? [];
    list.push(c);
    grouped.set(c.status, list);
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="sticky top-[57px] z-40 bg-surface/95 backdrop-blur-sm border-b border-border px-6 py-2.5">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-sm font-semibold text-foreground">Competitors</h1>
            <p className="text-[11px] text-muted">
              {competitors.length} total ·{" "}
              {Array.from(latestByCompetitor.values()).length} analysiert
            </p>
          </div>
          <div className="text-[10px] text-muted">
            Sag dem Agent &ldquo;analysiere [competitor name]&rdquo;
          </div>
        </div>
      </div>

      <main className="p-6 space-y-8">
        {["active", "watching", "excluded"].map((status) => {
          const items = grouped.get(status) ?? [];
          if (items.length === 0) return null;
          const meta = STATUS_LABELS[status];
          return (
            <section key={status}>
              <div className="flex items-center gap-2 mb-3">
                <span
                  className={`text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-md border ${meta.className}`}
                >
                  {meta.label}
                </span>
                <span className="text-[10px] text-muted font-mono">
                  {items.length}
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {items.map((c) => {
                  const latest = latestByCompetitor.get(c.id);
                  return (
                    <button
                      key={c.id}
                      onClick={() => setSelected(c)}
                      className="text-left bg-surface border border-border rounded-xl p-4 hover:border-primary/30 transition-colors"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex-1 min-w-0">
                          <h3 className="font-semibold text-foreground leading-tight">
                            {c.name}
                          </h3>
                          {c.market && (
                            <div className="text-[11px] text-muted mt-0.5">
                              {c.market}
                            </div>
                          )}
                        </div>
                        {latest && (
                          <span className="shrink-0 text-[10px] font-semibold bg-accent/10 text-accent px-2 py-1 rounded-md">
                            {latest.ads_count} ads
                          </span>
                        )}
                      </div>

                      <div className="mt-3 space-y-1 text-[11px]">
                        <div className="flex items-center gap-2">
                          <span className="text-muted w-24 shrink-0">FB Page ID</span>
                          <span
                            className={`font-mono ${
                              c.facebook_page_id
                                ? "text-foreground"
                                : "text-red-400/70"
                            }`}
                          >
                            {c.facebook_page_id ?? "— fehlt —"}
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <span className="text-muted w-24 shrink-0">Last analyzed</span>
                          <span className="text-foreground">
                            {fmtDate(c.last_analyzed_at)}
                          </span>
                        </div>
                      </div>

                      {c.notes && (
                        <p className="mt-3 text-[11px] text-muted italic leading-relaxed line-clamp-2">
                          {c.notes}
                        </p>
                      )}
                    </button>
                  );
                })}
              </div>
            </section>
          );
        })}
      </main>

      {selected && (
        <CompetitorDetail
          competitor={selected}
          analysis={latestByCompetitor.get(selected.id) ?? null}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------

function CompetitorDetail({
  competitor,
  analysis,
  onClose,
}: {
  competitor: Competitor;
  analysis: CompetitorAnalysis | null;
  onClose: () => void;
}) {
  const insights = analysis?.summary_json?.insights ?? analysis?.summary_json ?? null;

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/90 backdrop-blur-md flex items-center justify-center p-6"
      onClick={onClose}
    >
      <div
        className="w-full max-w-3xl max-h-[92vh] bg-[#0f0f11] border border-white/10 rounded-2xl overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 z-10 bg-[#0f0f11]/95 backdrop-blur-sm border-b border-white/10 p-6 flex items-start justify-between gap-4">
          <div>
            <div className="text-[10px] text-white/40 uppercase tracking-wider font-semibold">
              {competitor.market ?? "—"}
            </div>
            <h2 className="text-white font-semibold text-xl mt-0.5">
              {competitor.name}
            </h2>
            <div className="flex items-center gap-3 text-[11px] text-white/40 mt-2 font-mono">
              {competitor.facebook_page_id && (
                <span>FB {competitor.facebook_page_id}</span>
              )}
              {competitor.website && (
                <a
                  href={competitor.website}
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-white transition-colors underline"
                >
                  Website
                </a>
              )}
              {competitor.trustpilot_url && (
                <a
                  href={competitor.trustpilot_url}
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-white transition-colors underline"
                >
                  Trustpilot
                </a>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-9 h-9 flex items-center justify-center rounded-full bg-white/10 text-white/60 hover:text-white hover:bg-white/20 transition-colors text-xl"
          >
            ×
          </button>
        </div>

        <div className="p-6 text-white">
          {!analysis && (
            <div className="text-sm text-white/60 leading-relaxed">
              Noch keine Analyse für diesen Competitor.
              <br />
              Sag dem Agent:{" "}
              <code className="bg-white/10 px-2 py-0.5 rounded text-xs">
                analysiere {competitor.name}
              </code>
            </div>
          )}

          {analysis && insights && (
            <div className="space-y-6">
              <div className="text-[11px] text-white/40 font-mono">
                Analysed {fmtDate(analysis.created_at)} · {analysis.ads_count} ads
              </div>

              {insights.oversaturated_angles && insights.oversaturated_angles.length > 0 && (
                <section>
                  <h3 className="text-[11px] uppercase tracking-wider text-white/40 font-semibold mb-2">
                    Oversaturated Angles
                  </h3>
                  <div className="space-y-2">
                    {insights.oversaturated_angles.map((a: any, i: number) => (
                      <div key={i} className="bg-white/5 rounded-lg p-3">
                        <div className="text-sm font-medium text-white">{a.angle}</div>
                        {a.evidence && (
                          <div className="text-xs text-white/60 mt-1 leading-relaxed">
                            {a.evidence}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {insights.underexploited_angles && insights.underexploited_angles.length > 0 && (
                <section>
                  <h3 className="text-[11px] uppercase tracking-wider text-emerald-400 font-semibold mb-2">
                    Whitespace für Ora
                  </h3>
                  <div className="space-y-2">
                    {insights.underexploited_angles.map((a: any, i: number) => (
                      <div
                        key={i}
                        className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3"
                      >
                        <div className="text-sm font-medium text-white">{a.angle}</div>
                        {a.ora_move && (
                          <div className="text-xs text-emerald-200/80 mt-1 leading-relaxed">
                            → {a.ora_move}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {insights.ora_differentiation && insights.ora_differentiation.length > 0 && (
                <section>
                  <h3 className="text-[11px] uppercase tracking-wider text-white/40 font-semibold mb-2">
                    Ora Differentiation
                  </h3>
                  <div className="space-y-2">
                    {insights.ora_differentiation.map((r: any, i: number) => (
                      <div key={i} className="bg-white/5 rounded-lg p-3">
                        <div className="flex items-start gap-2">
                          <span
                            className={`text-[9px] uppercase font-bold px-1.5 py-0.5 rounded ${
                              r.priority === "high"
                                ? "bg-red-500/20 text-red-400"
                                : r.priority === "medium"
                                ? "bg-amber-500/20 text-amber-400"
                                : "bg-white/10 text-white/60"
                            }`}
                          >
                            {r.priority ?? "—"}
                          </span>
                          <div className="flex-1">
                            <div className="text-sm font-medium text-white">
                              {r.recommendation}
                            </div>
                            {r.concrete_action && (
                              <div className="text-xs text-white/70 mt-1 leading-relaxed">
                                → {r.concrete_action}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {insights.health_claim_risks_observed &&
                insights.health_claim_risks_observed.length > 0 && (
                  <section>
                    <h3 className="text-[11px] uppercase tracking-wider text-red-400 font-semibold mb-2">
                      Health Claim Risks
                    </h3>
                    <div className="space-y-2">
                      {insights.health_claim_risks_observed.map((r: any, i: number) => (
                        <div
                          key={i}
                          className="bg-red-500/10 border border-red-500/20 rounded-lg p-3"
                        >
                          <div className="text-xs text-white/60">{r.brand}</div>
                          <div className="text-sm text-white italic mt-1">
                            &ldquo;{r.claim}&rdquo;
                          </div>
                          {r.ora_must_avoid && (
                            <div className="text-xs text-red-200/80 mt-2 leading-relaxed">
                              Ora stattdessen: {r.ora_must_avoid}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </section>
                )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
