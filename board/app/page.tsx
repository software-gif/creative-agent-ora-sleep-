"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { useBrand } from "@/lib/brand-context";
import CreativeCard, {
  Creative,
  ANGLE_EMOJI,
  getImageUrl,
} from "@/components/CreativeCard";
import ImageOverlay from "@/components/ImageOverlay";
import SaveButton from "@/components/SaveButton";
import ClearBoardButton from "@/components/ClearBoardButton";

export default function Board() {
  const { brandId, loading: brandLoading } = useBrand();
  const [creatives, setCreatives] = useState<Creative[]>([]);
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [selectedImage, setSelectedImage] = useState<Creative | null>(null);

  useEffect(() => {
    if (!brandId) return;

    setLoading(true);
    loadCreatives(brandId);

    const channel = supabase
      .channel(`creatives-board-${brandId}`)
      .on(
        "postgres_changes",
        {
          event: "*",
          schema: "public",
          table: "creatives",
          filter: `brand_id=eq.${brandId}`,
        },
        (payload) => {
          if (payload.eventType === "INSERT") {
            const c = payload.new as Creative;
            if (!c.is_saved) {
              setCreatives((prev) => [c, ...prev]);
            }
          } else if (payload.eventType === "UPDATE") {
            const c = payload.new as Creative;
            if (c.is_saved) {
              // Saved → remove from board
              setCreatives((prev) => prev.filter((x) => x.id !== c.id));
            } else {
              setCreatives((prev) =>
                prev.map((x) => (x.id === c.id ? c : x))
              );
            }
          } else if (payload.eventType === "DELETE") {
            setCreatives((prev) =>
              prev.filter((c) => c.id !== (payload.old as Creative).id)
            );
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [brandId]);

  async function loadCreatives(bid: string) {
    const { data, error } = await supabase
      .from("creatives")
      .select("*")
      .eq("brand_id", bid)
      .eq("is_saved", false)
      .order("created_at", { ascending: false });

    if (!error && data) {
      setCreatives(data);
    }
    setLoading(false);
  }

  const angles = [...new Set(creatives.map((c) => c.angle))];
  const filtered =
    filter === "all" ? creatives : creatives.filter((c) => c.angle === filter);
  const doneCount = creatives.filter((c) => c.status === "done").length;

  if (brandLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-gray-400">
        Laden...
      </div>
    );
  }

  if (!brandId) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-gray-400">
        <p className="text-lg font-medium">Keine Brand konfiguriert</p>
        <p className="text-sm mt-1">
          Lege zuerst eine Brand in der Datenbank an.
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Filter Bar */}
      <div className="sticky top-[57px] z-40 bg-white border-b border-gray-200 px-6 py-2 flex items-center justify-between">
        <span className="text-xs text-gray-400 bg-gray-100 px-2 py-0.5 rounded">
          {doneCount} Creatives
        </span>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          className="text-sm border border-gray-200 rounded-lg px-3 py-1.5 text-gray-600 focus:outline-none focus:border-amber-700"
        >
          <option value="all">Alle Angles</option>
          {angles.map((a) => (
            <option key={a} value={a}>
              {ANGLE_EMOJI[a] || ""} {a} (
              {creatives.filter((c) => c.angle === a).length})
            </option>
          ))}
        </select>
      </div>

      {/* Grid */}
      <main className="p-6">
        {loading ? (
          <div className="flex items-center justify-center h-64 text-gray-400">
            Laden...
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 text-gray-400">
            <p className="text-lg font-medium">Noch keine Creatives</p>
            <p className="text-sm mt-1">
              Generiere Ads per Claude Code — sie erscheinen hier automatisch.
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
                  creative.status === "done" && (
                    <>
                      <SaveButton creative={creative} />
                      {getImageUrl(creative) && (
                        <a
                          href={getImageUrl(creative)!}
                          download
                          className="flex-1 text-center text-xs font-semibold bg-gray-900 text-white py-1.5 rounded-lg hover:bg-gray-700 transition-colors"
                        >
                          Download
                        </a>
                      )}
                    </>
                  )
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

      <ClearBoardButton />
    </div>
  );
}
