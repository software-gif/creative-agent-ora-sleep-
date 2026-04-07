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

type CreativeCardProps = {
  creative: Creative;
  onImageClick?: (creative: Creative) => void;
  actions?: React.ReactNode;
  draggable?: boolean;
  onDragStart?: (e: React.DragEvent, creative: Creative) => void;
};

export default function CreativeCard({
  creative,
  onImageClick,
  actions,
  draggable,
  onDragStart,
}: CreativeCardProps) {
  const imageUrl = getImageUrl(creative);

  return (
    <div
      className="bg-white rounded-xl border border-gray-200 overflow-hidden shadow-sm hover:shadow-md transition-shadow"
      draggable={draggable}
      onDragStart={(e) => onDragStart?.(e, creative)}
    >
      {/* Image */}
      <div
        className="relative aspect-[4/5] bg-gray-100 cursor-pointer"
        onClick={() => imageUrl && onImageClick?.(creative)}
      >
        {creative.status === "generating" ? (
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="w-10 h-10 border-3 border-amber-600 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : imageUrl ? (
          <img
            src={imageUrl}
            alt={creative.sub_angle}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-gray-300 text-sm">
            Kein Bild
          </div>
        )}
        <span className="absolute top-2 right-2 bg-white/90 text-[10px] font-semibold px-1.5 py-0.5 rounded">
          {creative.format}
        </span>
      </div>

      {/* Meta */}
      <div className="p-3">
        <div
          className={`text-[11px] font-semibold uppercase tracking-wide ${ANGLE_COLORS[creative.angle] || "text-gray-500"}`}
        >
          {ANGLE_EMOJI[creative.angle]} {creative.angle}
        </div>
        <div className="text-sm font-semibold text-gray-900 mt-0.5 leading-tight">
          {creative.sub_angle}
        </div>
        {creative.hook_text && (
          <div className="text-xs text-gray-400 mt-1 italic line-clamp-2">
            {creative.hook_text}
          </div>
        )}
        {actions && <div className="mt-2 flex items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
}
