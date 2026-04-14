"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { supabase } from "@/lib/supabase";
import { useBrand } from "@/lib/brand-context";
import CreativeCard, {
  Creative,
  getImageUrl,
  downloadCreative,
} from "@/components/CreativeCard";
import ImageOverlay from "@/components/ImageOverlay";
import ApprovedListView from "@/components/ApprovedListView";
import { VariablesPanel, TemplatesPanel } from "@/components/MetaPanels";
import {
  MetaVariable,
  MetaTemplate,
  renderTemplate,
  systemVars,
  downloadCsv,
} from "@/lib/meta-upload";

type MetaField =
  | "meta_ad_name"
  | "meta_campaign"
  | "meta_ad_set"
  | "meta_destination_url";

export default function Approved() {
  const { brandId, loading: brandLoading } = useBrand();
  const [creatives, setCreatives] = useState<Creative[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedImage, setSelectedImage] = useState<Creative | null>(null);
  const [statusFilter, setStatusFilter] = useState<"all" | "approved" | "live">(
    "all"
  );
  const [view, setView] = useState<"list" | "grid">("list");
  const [selected, setSelected] = useState<Set<string>>(new Set());

  // Variables + Templates
  const [variables, setVariables] = useState<MetaVariable[]>([]);
  const [templates, setTemplates] = useState<MetaTemplate[]>([]);
  const [variablesOpen, setVariablesOpen] = useState(false);
  const [templatesOpen, setTemplatesOpen] = useState(false);

  // ------------------------- Data loading -------------------------

  useEffect(() => {
    if (!brandId) return;

    setLoading(true);
    loadApproved(brandId);
    loadVariables(brandId);
    loadTemplates(brandId);

    const channel = supabase
      .channel(`creatives-approved-${brandId}`)
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "creatives",
          filter: `brand_id=eq.${brandId}`,
        },
        (payload) => {
          if (payload.eventType === "UPDATE") {
            const c = payload.new as Creative;
            if (
              c.approval_status === "approved" ||
              c.approval_status === "live"
            ) {
              setCreatives((prev) => {
                const exists = prev.find((x) => x.id === c.id);
                if (exists) return prev.map((x) => (x.id === c.id ? c : x));
                return [c, ...prev];
              });
            } else {
              setCreatives((prev) => prev.filter((x) => x.id !== c.id));
            }
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [brandId]);

  async function loadApproved(bid: string) {
    const { data, error } = await supabase
      .from("creatives")
      .select("*")
      .eq("brand_id", bid)
      .in("approval_status", ["approved", "live"])
      .order("created_at", { ascending: false });
    if (!error && data) setCreatives(data);
    setLoading(false);
  }

  async function loadVariables(bid: string) {
    const { data } = await supabase
      .from("meta_variables")
      .select("*")
      .eq("brand_id", bid)
      .order("key");
    setVariables((data as MetaVariable[]) ?? []);
  }

  async function loadTemplates(bid: string) {
    const { data } = await supabase
      .from("meta_templates")
      .select("*")
      .eq("brand_id", bid)
      .order("is_default", { ascending: false })
      .order("name");
    setTemplates((data as MetaTemplate[]) ?? []);
  }

  // ------------------------- Mutations -------------------------

  async function markAsLive(id: string) {
    await supabase
      .from("creatives")
      .update({ approval_status: "live" })
      .eq("id", id);
  }

  async function revokeApproval(id: string) {
    await supabase
      .from("creatives")
      .update({ approval_status: "draft" })
      .eq("id", id);
  }

  async function updateField(
    id: string,
    field: MetaField,
    value: string
  ): Promise<void> {
    const { error } = await supabase
      .from("creatives")
      .update({ [field]: value })
      .eq("id", id);
    if (error) throw error;
  }

  async function updateReady(id: string, ready: boolean): Promise<void> {
    await supabase.from("creatives").update({ meta_ready: ready }).eq("id", id);
  }

  // ------------------------- Selection -------------------------

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleSelectAll(all: boolean) {
    if (all) {
      setSelected(new Set(filtered.map((c) => c.id)));
    } else {
      setSelected(new Set());
    }
  }

  function clearSelection() {
    setSelected(new Set());
  }

  // ------------------------- Bulk actions -------------------------

  const defaultTemplate = useMemo(
    () => templates.find((t) => t.is_default) || templates[0] || null,
    [templates]
  );

  const reservedKeys = useMemo(() => {
    // A fake creative just to enumerate system var keys
    const dummy: Creative = { id: "00000000", format: "4:5" } as Creative;
    return Object.keys(systemVars(dummy));
  }, []);

  const availableKeys = useMemo(() => {
    return [...reservedKeys, ...variables.map((v) => v.key)];
  }, [reservedKeys, variables]);

  async function bulkApplyTemplate(templateId?: string) {
    const tpl = templateId
      ? templates.find((t) => t.id === templateId)
      : defaultTemplate;
    if (!tpl) {
      alert("Kein Template definiert. Klick auf 'Templates' oben rechts.");
      return;
    }
    const selectedList = filtered.filter((c) => selected.has(c.id));
    for (const c of selectedList) {
      const rendered = renderTemplate(tpl.template_string, c, variables);
      await updateField(c.id, "meta_ad_name", rendered);
    }
    await loadApproved(brandId!);
  }

  async function bulkApplyField(field: MetaField) {
    const value = prompt(
      `Welchen Wert für ${field.replace("meta_", "")} setzen? (für ${selected.size} ausgewählte Creatives)`
    );
    if (value == null) return;
    const selectedList = filtered.filter((c) => selected.has(c.id));
    for (const c of selectedList) {
      // Render template if it contains {{}} tokens
      const rendered = /\{\{/.test(value)
        ? renderTemplate(value, c, variables)
        : value;
      await updateField(c.id, field, rendered);
    }
    await loadApproved(brandId!);
  }

  async function bulkMarkReady() {
    const selectedList = filtered.filter((c) => selected.has(c.id));
    for (const c of selectedList) {
      await updateReady(c.id, true);
    }
    await loadApproved(brandId!);
  }

  function exportSelected() {
    const selectedList = filtered.filter((c) => selected.has(c.id));
    if (selectedList.length === 0) return;
    downloadCsv(selectedList);
  }

  function exportAll() {
    if (filtered.length === 0) return;
    downloadCsv(filtered);
  }

  // ------------------------- Filtering -------------------------

  const filtered =
    statusFilter === "all"
      ? creatives
      : creatives.filter((c) => c.approval_status === statusFilter);

  const approvedCount = creatives.filter(
    (c) => c.approval_status === "approved"
  ).length;
  const liveCount = creatives.filter((c) => c.approval_status === "live").length;
  const readyCount = filtered.filter((c) => c.meta_ready).length;

  // ------------------------- Render -------------------------

  if (brandLoading) {
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

  return (
    <div className="min-h-screen bg-background">
      {/* Top bar */}
      <div className="sticky top-[57px] z-40 bg-surface/95 backdrop-blur-sm border-b border-border px-6 py-2.5">
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-foreground tabular-nums">
              {filtered.length}
              <span className="text-muted font-normal"> / {creatives.length}</span>
            </span>
            {approvedCount > 0 && (
              <span className="flex items-center gap-1 text-xs text-green-600 font-medium">
                <span className="w-1.5 h-1.5 bg-green-500 rounded-full" />
                {approvedCount} bereit
              </span>
            )}
            {liveCount > 0 && (
              <span className="flex items-center gap-1 text-xs text-blue-600 font-medium">
                <span className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
                {liveCount} live
              </span>
            )}
            {readyCount > 0 && (
              <span className="flex items-center gap-1 text-xs text-emerald-600 font-medium">
                <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full" />
                {readyCount} ready for Meta
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            {/* View toggle */}
            <div className="flex items-center bg-background rounded-lg p-0.5 gap-0.5">
              {(["list", "grid"] as const).map((v) => (
                <button
                  key={v}
                  onClick={() => setView(v)}
                  className={`text-[11px] font-medium px-2 py-1 rounded-md transition-all ${
                    view === v
                      ? "bg-surface text-primary shadow-sm"
                      : "text-muted hover:text-foreground"
                  }`}
                >
                  {v === "list" ? "List" : "Grid"}
                </button>
              ))}
            </div>

            {/* Status filter */}
            <div className="flex items-center bg-background rounded-lg p-0.5 gap-0.5">
              {(["all", "approved", "live"] as const).map((s) => (
                <button
                  key={s}
                  onClick={() => setStatusFilter(s)}
                  className={`text-[11px] font-medium px-2 py-1 rounded-md transition-all ${
                    statusFilter === s
                      ? "bg-surface text-primary shadow-sm"
                      : "text-muted hover:text-foreground"
                  }`}
                >
                  {s === "all" ? "Alle" : s === "approved" ? "Bereit" : "Live"}
                </button>
              ))}
            </div>

            {/* Variables / Templates buttons */}
            <button
              onClick={() => setVariablesOpen(true)}
              className="text-[11px] font-medium text-muted hover:text-foreground bg-background hover:bg-surface border border-border px-2.5 py-1 rounded-lg transition-colors"
              title="User-Variablen bearbeiten"
            >
              ⚙ Variables ({variables.length})
            </button>
            <button
              onClick={() => setTemplatesOpen(true)}
              className="text-[11px] font-medium text-muted hover:text-foreground bg-background hover:bg-surface border border-border px-2.5 py-1 rounded-lg transition-colors"
              title="Naming-Templates bearbeiten"
            >
              📋 Templates ({templates.length})
            </button>
            <button
              onClick={exportAll}
              disabled={filtered.length === 0}
              className="text-[11px] font-semibold bg-primary text-white px-3 py-1.5 rounded-lg hover:bg-primary/90 disabled:opacity-40 transition-colors"
              title="Alle sichtbaren Creatives als CSV exportieren"
            >
              Export CSV ({filtered.length})
            </button>
          </div>
        </div>
      </div>

      {/* Bulk actions bar (shows when rows selected) */}
      {selected.size > 0 && (
        <div className="sticky top-[105px] z-30 bg-primary/5 border-b border-primary/20 px-6 py-2">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold text-primary">
                {selected.size} selected
              </span>
              <button
                onClick={clearSelection}
                className="text-[10px] text-muted hover:text-foreground px-2 py-0.5 rounded hover:bg-background transition-colors"
              >
                clear
              </button>
            </div>
            <div className="flex items-center gap-1.5 flex-wrap">
              <button
                onClick={() => bulkApplyTemplate()}
                className="text-[11px] font-semibold bg-surface border border-border text-foreground px-2.5 py-1 rounded-lg hover:border-primary/50 transition-colors"
                title={defaultTemplate?.template_string || "No default template"}
              >
                Apply Naming
                {defaultTemplate && (
                  <span className="text-muted font-normal ml-1">
                    ({defaultTemplate.name})
                  </span>
                )}
              </button>
              <button
                onClick={() => bulkApplyField("meta_campaign")}
                className="text-[11px] font-semibold bg-surface border border-border text-foreground px-2.5 py-1 rounded-lg hover:border-primary/50 transition-colors"
              >
                Apply Campaign
              </button>
              <button
                onClick={() => bulkApplyField("meta_ad_set")}
                className="text-[11px] font-semibold bg-surface border border-border text-foreground px-2.5 py-1 rounded-lg hover:border-primary/50 transition-colors"
              >
                Apply Ad Set
              </button>
              <button
                onClick={() => bulkApplyField("meta_destination_url")}
                className="text-[11px] font-semibold bg-surface border border-border text-foreground px-2.5 py-1 rounded-lg hover:border-primary/50 transition-colors"
              >
                Apply Dest URL
              </button>
              <button
                onClick={bulkMarkReady}
                className="text-[11px] font-semibold bg-emerald-500 text-white px-2.5 py-1 rounded-lg hover:bg-emerald-600 transition-colors"
              >
                ✓ Mark Ready
              </button>
              <button
                onClick={exportSelected}
                className="text-[11px] font-semibold bg-primary text-white px-2.5 py-1 rounded-lg hover:bg-primary/90 transition-colors"
              >
                Export Selected CSV
              </button>
            </div>
          </div>
        </div>
      )}

      <main className="p-6">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-muted">
            Laden...
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-80 text-muted">
            <div className="w-16 h-16 rounded-2xl bg-green-500/10 flex items-center justify-center mb-4">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={1.5}
                className="w-8 h-8 text-green-500"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
            </div>
            <p className="text-lg font-semibold text-foreground">
              Noch keine Approved Creatives
            </p>
            <p className="text-sm mt-1 max-w-xs text-center">
              Approve Creatives auf dem Board — sie erscheinen dann hier für den Meta-Upload-Flow.
            </p>
          </div>
        ) : view === "list" ? (
          <ApprovedListView
            creatives={filtered}
            selected={selected}
            onToggleSelect={toggleSelect}
            onToggleSelectAll={toggleSelectAll}
            onFieldChange={updateField}
            onReadyChange={updateReady}
            onOpenPreview={setSelectedImage}
            onMarkLive={markAsLive}
            onRevoke={revokeApproval}
            variableKeys={availableKeys}
          />
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6 gap-5">
            {filtered.map((creative) => (
              <CreativeCard
                key={creative.id}
                creative={creative}
                onImageClick={setSelectedImage}
                actions={
                  <>
                    {creative.approval_status === "approved" && (
                      <button
                        onClick={() => markAsLive(creative.id)}
                        className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-blue-500 text-white hover:bg-blue-600 transition-colors"
                      >
                        Live
                      </button>
                    )}
                    {creative.approval_status === "live" && (
                      <span className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-blue-100 text-blue-700">
                        <span className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
                        Live
                      </span>
                    )}
                    {getImageUrl(creative) && (
                      <button
                        onClick={() => downloadCreative(creative)}
                        className="flex-1 text-center text-xs font-semibold bg-primary text-white py-1.5 rounded-lg hover:bg-primary/80 transition-colors"
                      >
                        Download
                      </button>
                    )}
                    <button
                      onClick={() => revokeApproval(creative.id)}
                      className="p-1.5 rounded-lg text-muted hover:text-red-500 hover:bg-red-50 transition-colors"
                      title="Zurück zu Draft"
                    >
                      ↶
                    </button>
                  </>
                }
              />
            ))}
          </div>
        )}
      </main>

      <ImageOverlay
        creative={selectedImage}
        onClose={() => setSelectedImage(null)}
      />

      <VariablesPanel
        brandId={brandId!}
        open={variablesOpen}
        onClose={() => setVariablesOpen(false)}
        onChanged={() => loadVariables(brandId!)}
        reservedKeys={reservedKeys}
      />

      <TemplatesPanel
        brandId={brandId!}
        open={templatesOpen}
        onClose={() => setTemplatesOpen(false)}
        onChanged={() => loadTemplates(brandId!)}
        availableKeys={availableKeys}
      />
    </div>
  );
}
