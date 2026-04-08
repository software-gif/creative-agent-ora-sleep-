"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { useBrand } from "@/lib/brand-context";
import CreativeCard, { Creative, getImageUrl, downloadCreative } from "@/components/CreativeCard";
import ImageOverlay from "@/components/ImageOverlay";

export default function Approved() {
  const { brandId, loading: brandLoading } = useBrand();
  const [creatives, setCreatives] = useState<Creative[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedImage, setSelectedImage] = useState<Creative | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  useEffect(() => {
    if (!brandId) return;

    setLoading(true);
    loadApproved(brandId);

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
            if (c.approval_status === "approved" || c.approval_status === "live") {
              setCreatives((prev) => {
                const exists = prev.find((x) => x.id === c.id);
                if (exists) {
                  return prev.map((x) => (x.id === c.id ? c : x));
                }
                return [c, ...prev];
              });
            } else {
              // No longer approved → remove
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

    if (!error && data) {
      setCreatives(data);
    }
    setLoading(false);
  }

  async function markAsLive(creativeId: string) {
    await supabase
      .from("creatives")
      .update({ approval_status: "live" })
      .eq("id", creativeId);
  }

  async function revokeApproval(creativeId: string) {
    await supabase
      .from("creatives")
      .update({ approval_status: "draft" })
      .eq("id", creativeId);
  }

  const filtered = statusFilter === "all"
    ? creatives
    : creatives.filter((c) => c.approval_status === statusFilter);

  const approvedCount = creatives.filter((c) => c.approval_status === "approved").length;
  const liveCount = creatives.filter((c) => c.approval_status === "live").length;

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
      {/* Status bar */}
      <div className="sticky top-[57px] z-40 bg-surface/95 backdrop-blur-sm border-b border-border px-6 py-2">
        <div className="flex items-center justify-between">
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
          </div>
          <div className="flex items-center bg-background rounded-lg p-0.5 gap-0.5">
            {(["all", "approved", "live"] as const).map((s) => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={`text-[11px] font-medium px-2 py-1 rounded-md transition-all ${
                  statusFilter === s ? "bg-surface text-primary shadow-sm" : "text-muted hover:text-foreground"
                }`}
              >
                {s === "all" ? "Alle" : s === "approved" ? "Bereit" : "Live"}
              </button>
            ))}
          </div>
        </div>
      </div>

      <main className="p-6">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-muted">
            Laden...
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-80 text-muted">
            <div className="w-16 h-16 rounded-2xl bg-green-500/10 flex items-center justify-center mb-4">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-8 h-8 text-green-500">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-lg font-semibold text-foreground">Noch keine Approved Creatives</p>
            <p className="text-sm mt-1 max-w-xs text-center">
              Approve Creatives auf dem Board — sie erscheinen dann hier zum Upload.
            </p>
          </div>
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
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5">
                          <path d="M3.196 12.87l-.825.483a.75.75 0 000 1.294l7.25 4.25a.75.75 0 00.758 0l7.25-4.25a.75.75 0 000-1.294l-.825-.484-5.666 3.322a2.25 2.25 0 01-2.276 0L3.196 12.87z" />
                          <path d="M3.196 8.87l-.825.483a.75.75 0 000 1.294l7.25 4.25a.75.75 0 00.758 0l7.25-4.25a.75.75 0 000-1.294l-.825-.484-5.666 3.322a2.25 2.25 0 01-2.276 0L3.196 8.87z" />
                          <path d="M10.38 1.103a.75.75 0 00-.76 0l-7.25 4.25a.75.75 0 000 1.294l7.25 4.25a.75.75 0 00.76 0l7.25-4.25a.75.75 0 000-1.294l-7.25-4.25z" />
                        </svg>
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
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} className="w-4 h-4">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 15L3 9m0 0l6-6M3 9h12a6 6 0 010 12h-3" />
                      </svg>
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
    </div>
  );
}
