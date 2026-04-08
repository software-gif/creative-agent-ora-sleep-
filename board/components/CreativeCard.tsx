"use client";

import { supabase } from "@/lib/supabase";

export type Creative = {
  id: string;
  brand_id: string;
  batch_id: string | null;
  angle: string;
  sub_angle: string;
  hook_text: string;
  format: string;
  variant: number;
  status: string;
  image_url: string | null;
  storage_path: string | null;
  is_saved: boolean;
  approval_status: string; // draft | approved | live
  creative_number: number | null;
  creative_style: string;
  creative_type: string;
  season: string;
  environment: string | null;
  product_category: string | null;
  created_at: string;
};

export const ANGLE_COLORS: Record<string, string> = {
  "Problem/Pain": "text-red-500",
  Benefit: "text-green-500",
  Proof: "text-blue-500",
  Curiosity: "text-purple-500",
  Education: "text-sky-500",
  Story: "text-pink-500",
  Offer: "text-amber-500",
};

export const ANGLE_EMOJI: Record<string, string> = {
  "Problem/Pain": "🔥",
  Benefit: "✨",
  Proof: "✅",
  Curiosity: "🔮",
  Education: "📚",
  Story: "💜",
  Offer: "🏷️",
};

export function getImageUrl(creative: Creative): string | null {
  if (creative.image_url) return creative.image_url;
  if (creative.storage_path) {
    const { data } = supabase.storage
      .from("creatives")
      .getPublicUrl(creative.storage_path);
    return data.publicUrl;
  }
  return null;
}

export function getDownloadFilename(creative: Creative): string {
  const slug = creative.sub_angle.toLowerCase().replace(/\s+/g, "_").replace(/[^a-z0-9_]/g, "");
  return `${creative.angle}_${slug}_${creative.format.replace(":", "x")}.png`;
}

export async function downloadCreative(creative: Creative) {
  const imageUrl = getImageUrl(creative);
  if (!imageUrl) return;
  try {
    const resp = await fetch(`/api/download?url=${encodeURIComponent(imageUrl)}&filename=img`);
    const blob = await resp.blob();
    const blobUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = getDownloadFilename(creative);
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(blobUrl);
  } catch (e) {
    window.open(imageUrl, "_blank");
  }
}

type CreativeCardProps = {
  creative: Creative;
  onImageClick?: (creative: Creative) => void;
  onDelete?: (creative: Creative) => void;
  actions?: React.ReactNode;
  draggable?: boolean;
  onDragStart?: (e: React.DragEvent, creative: Creative) => void;
};

export default function CreativeCard({
  creative,
  onImageClick,
  onDelete,
  actions,
  draggable,
  onDragStart,
}: CreativeCardProps) {
  const imageUrl = getImageUrl(creative);

  return (
    <div
      className="group bg-surface rounded-xl border border-border overflow-hidden shadow-sm hover:shadow-md hover:border-primary/30 transition-all"
      draggable={draggable}
      onDragStart={(e) => onDragStart?.(e, creative)}
    >
      {/* Image */}
      <div
        className="relative aspect-[4/5] bg-background cursor-pointer overflow-hidden"
        onClick={() => imageUrl && onImageClick?.(creative)}
      >
        {creative.status === "generating" ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
            <div className="w-10 h-10 border-3 border-primary border-t-transparent rounded-full animate-spin" />
            <span className="text-xs text-muted">Wird generiert...</span>
          </div>
        ) : imageUrl ? (
          <img
            src={imageUrl}
            alt={creative.sub_angle}
            className="w-full h-full object-cover group-hover:scale-[1.02] transition-transform duration-300"
            loading="lazy"
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-muted gap-2">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5} className="w-8 h-8 opacity-40">
              <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 15.75l5.159-5.159a2.25 2.25 0 013.182 0l5.159 5.159m-1.5-1.5l1.409-1.409a2.25 2.25 0 013.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0022.5 18.75V5.25A2.25 2.25 0 0020.25 3H3.75A2.25 2.25 0 001.5 5.25v13.5A2.25 2.25 0 003.75 21z" />
            </svg>
            <span className="text-xs">Kein Bild</span>
          </div>
        )}
        {/* Top-left: ID + off-brand badge */}
        <div className="absolute top-2 left-2 flex gap-1">
          {creative.creative_number && (
            <span className="bg-black/60 backdrop-blur-sm text-white text-[10px] font-bold px-1.5 py-0.5 rounded shadow-sm font-mono">
              #{creative.creative_number}
            </span>
          )}
          {creative.creative_style === "off_brand" && (
            <span className="bg-orange-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded shadow-sm">
              OFF
            </span>
          )}
        </div>
        {/* Top-right: badges + delete */}
        <div className="absolute top-2 right-2 flex gap-1">
          {creative.creative_type === "lifestyle" && (
            <span className="bg-primary/90 text-white text-[10px] font-semibold px-1.5 py-0.5 rounded shadow-sm">
              Lifestyle
            </span>
          )}
          <span className="bg-white/90 backdrop-blur-sm text-[10px] font-semibold px-1.5 py-0.5 rounded shadow-sm">
            {creative.format}
          </span>
          {onDelete && (
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(creative); }}
              className="opacity-0 group-hover:opacity-100 bg-red-500/90 text-white w-5 h-5 flex items-center justify-center rounded shadow-sm hover:bg-red-600 transition-all"
              title="Löschen"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="w-3 h-3">
                <path fillRule="evenodd" d="M8.75 1A2.75 2.75 0 006 3.75v.443c-.795.077-1.584.176-2.365.298a.75.75 0 10.23 1.482l.149-.022.841 10.518A2.75 2.75 0 007.596 19h4.807a2.75 2.75 0 002.742-2.53l.841-10.519.149.023a.75.75 0 00.23-1.482A41.03 41.03 0 0014 4.193V3.75A2.75 2.75 0 0011.25 1h-2.5zM10 4c.84 0 1.673.025 2.5.075V3.75c0-.69-.56-1.25-1.25-1.25h-2.5c-.69 0-1.25.56-1.25 1.25v.325C8.327 4.025 9.16 4 10 4zM8.58 7.72a.75.75 0 00-1.5.06l.3 7.5a.75.75 0 101.5-.06l-.3-7.5zm4.34.06a.75.75 0 10-1.5-.06l-.3 7.5a.75.75 0 101.5.06l.3-7.5z" clipRule="evenodd" />
              </svg>
            </button>
          )}
        </div>
        {creative.approval_status === "approved" && (
          <span className="absolute bottom-2 left-2 bg-green-500/90 text-white text-[9px] font-bold px-1.5 py-0.5 rounded shadow-sm">
            ✓ Approved
          </span>
        )}
        {creative.approval_status === "live" && (
          <span className="absolute bottom-2 left-2 bg-blue-500/90 text-white text-[9px] font-bold px-1.5 py-0.5 rounded shadow-sm flex items-center gap-0.5">
            <span className="w-1 h-1 bg-white rounded-full animate-pulse" />
            Live
          </span>
        )}
      </div>

      {/* Meta */}
      <div className="p-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            <span className="text-sm">{ANGLE_EMOJI[creative.angle]}</span>
            <span className={`text-[11px] font-semibold uppercase tracking-wide ${ANGLE_COLORS[creative.angle] || "text-gray-500"}`}>
              {creative.angle}
            </span>
          </div>
          <div className="flex items-center gap-1">
            {creative.product_category && (
              <span className="text-[9px] font-medium text-muted bg-background px-1.5 py-0.5 rounded capitalize">
                {creative.product_category}
              </span>
            )}
            {creative.environment && (
              <span className="text-[9px] font-medium text-accent bg-accent/10 px-1.5 py-0.5 rounded capitalize">
                {creative.environment}
              </span>
            )}
          </div>
        </div>
        <div className="text-[13px] font-semibold text-foreground mt-1 leading-snug">
          {creative.sub_angle}
        </div>
        {creative.hook_text && (
          <div className="text-xs text-muted mt-1.5 leading-relaxed line-clamp-2">
            &ldquo;{creative.hook_text}&rdquo;
          </div>
        )}
        {actions && <div className="mt-2.5 flex items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}
