"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { useBrand } from "@/lib/brand-context";
import CreativeCard, { Creative, getImageUrl, downloadCreative } from "@/components/CreativeCard";
import ImageOverlay from "@/components/ImageOverlay";
import FolderSidebar from "@/components/FolderSidebar";

type SavedAsset = {
  id: string;
  creative_id: string;
  folder_id: string | null;
  creative: Creative;
};

export default function Library() {
  const { brandId, loading: brandLoading } = useBrand();
  const [assets, setAssets] = useState<SavedAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedFolder, setSelectedFolder] = useState<string | null>(null);
  const [selectedImage, setSelectedImage] = useState<Creative | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  useEffect(() => {
    if (brandId) loadAssets(brandId);
  }, [brandId]);

  async function loadAssets(bid: string) {
    setLoading(true);
    const { data, error } = await supabase
      .from("saved_assets")
      .select("*, creative:creatives(*)")
      .eq("brand_id", bid)
      .order("created_at", { ascending: false });

    if (!error && data) {
      const mapped = data.map((row: Record<string, unknown>) => ({
        id: row.id as string,
        creative_id: row.creative_id as string,
        folder_id: row.folder_id as string | null,
        creative: row.creative as Creative,
      }));
      setAssets(mapped);
    }
    setLoading(false);
  }

  async function markAsLive(creativeId: string) {
    const { error } = await supabase
      .from("creatives")
      .update({ approval_status: "live" })
      .eq("id", creativeId);
    if (error) return;

    setAssets((prev) =>
      prev.map((a) =>
        a.creative_id === creativeId
          ? { ...a, creative: { ...a.creative, approval_status: "live" } }
          : a
      )
    );
  }

  async function removeFromLibrary(creativeId: string) {
    const { error: deleteError } = await supabase
      .from("saved_assets")
      .delete()
      .eq("creative_id", creativeId);
    if (deleteError) return;

    await supabase
      .from("creatives")
      .update({ is_saved: false, approval_status: "draft" })
      .eq("id", creativeId);
    setAssets((prev) => prev.filter((a) => a.creative_id !== creativeId));
  }

  async function moveToFolder(folderId: string, creativeId: string) {
    const { error } = await supabase
      .from("saved_assets")
      .update({ folder_id: folderId })
      .eq("creative_id", creativeId);
    if (error) return;

    setAssets((prev) =>
      prev.map((a) =>
        a.creative_id === creativeId ? { ...a, folder_id: folderId } : a
      )
    );
  }

  function handleDragStart(e: React.DragEvent, creative: Creative) {
    e.dataTransfer.setData("creative-id", creative.id);
  }

  const filtered = assets
    .filter((a) => !selectedFolder || a.folder_id === selectedFolder)
    .filter((a) => statusFilter === "all" || a.creative.approval_status === statusFilter);

  const approvedCount = assets.filter((a) => a.creative.approval_status === "approved").length;
  const liveCount = assets.filter((a) => a.creative.approval_status === "live").length;

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
    <div className="flex min-h-screen bg-background">
      <FolderSidebar
        selectedFolderId={selectedFolder}
        onSelectFolder={setSelectedFolder}
        onDrop={moveToFolder}
      />

      <div className="flex-1 flex flex-col">
        {/* Status filter bar */}
        <div className="border-b border-border bg-surface/95 backdrop-blur-sm px-6 py-2 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xs font-semibold text-foreground tabular-nums">
              {filtered.length}
              <span className="text-muted font-normal"> Assets</span>
            </span>
            {approvedCount > 0 && (
              <span className="text-xs text-green-600 font-medium">
                {approvedCount} approved
              </span>
            )}
            {liveCount > 0 && (
              <span className="text-xs text-blue-600 font-medium">
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
                {s === "all" ? "Alle" : s === "approved" ? "Approved" : "Live"}
              </button>
            ))}
          </div>
        </div>

        <main className="flex-1 p-6">
          {loading ? (
            <div className="flex items-center justify-center h-64 text-muted">
              Laden...
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-muted">
              <p className="text-lg font-medium">
                {selectedFolder ? "Keine Assets in diesem Ordner" : "Noch keine gespeicherten Assets"}
              </p>
              <p className="text-sm mt-1">
                Approve Creatives auf dem Board, um sie hier zu organisieren.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-5">
              {filtered.map((asset) => (
                <CreativeCard
                  key={asset.id}
                  creative={asset.creative}
                  onImageClick={setSelectedImage}
                  draggable
                  onDragStart={handleDragStart}
                  actions={
                    <>
                      {asset.creative.approval_status === "approved" && (
                        <button
                          onClick={() => markAsLive(asset.creative_id)}
                          className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-blue-500 text-white hover:bg-blue-600 transition-colors"
                          title="Als Live markieren (zu Meta hochgeladen)"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-3.5 h-3.5">
                            <path d="M3.196 12.87l-.825.483a.75.75 0 000 1.294l7.25 4.25a.75.75 0 00.758 0l7.25-4.25a.75.75 0 000-1.294l-.825-.484-5.666 3.322a2.25 2.25 0 01-2.276 0L3.196 12.87z" />
                            <path d="M3.196 8.87l-.825.483a.75.75 0 000 1.294l7.25 4.25a.75.75 0 00.758 0l7.25-4.25a.75.75 0 000-1.294l-.825-.484-5.666 3.322a2.25 2.25 0 01-2.276 0L3.196 8.87z" />
                            <path d="M10.38 1.103a.75.75 0 00-.76 0l-7.25 4.25a.75.75 0 000 1.294l7.25 4.25a.75.75 0 00.76 0l7.25-4.25a.75.75 0 000-1.294l-7.25-4.25z" />
                          </svg>
                          Live
                        </button>
                      )}
                      {asset.creative.approval_status === "live" && (
                        <span className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-blue-100 text-blue-700">
                          <span className="w-1.5 h-1.5 bg-blue-500 rounded-full" />
                          Live
                        </span>
                      )}
                      {getImageUrl(asset.creative) && (
                        <button
                          onClick={() => downloadCreative(asset.creative)}
                          className="flex-1 text-center text-xs font-semibold bg-primary text-white py-1.5 rounded-lg hover:bg-primary/80 transition-colors"
                        >
                          Download
                        </button>
                      )}
                      <button
                        onClick={() => removeFromLibrary(asset.creative_id)}
                        className="p-1.5 rounded-lg text-muted hover:text-red-500 hover:bg-red-50 transition-colors"
                        title="Aus Library entfernen"
                      >
                        <svg
                          xmlns="http://www.w3.org/2000/svg"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth={2}
                          className="w-4 h-4"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M6 18L18 6M6 6l12 12"
                          />
                        </svg>
                      </button>
                    </>
                  }
                />
              ))}
            </div>
          )}
        </main>
      </div>

      <ImageOverlay
        creative={selectedImage}
        onClose={() => setSelectedImage(null)}
      />
    </div>
  );
}
