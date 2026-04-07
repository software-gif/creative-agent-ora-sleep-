"use client";

import { Creative, getImageUrl } from "./CreativeCard";

type ImageOverlayProps = {
  creative: Creative | null;
  onClose: () => void;
};

export default function ImageOverlay({ creative, onClose }: ImageOverlayProps) {
  if (!creative) return null;

  const imageUrl = getImageUrl(creative);
  if (!imageUrl) return null;

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/80 backdrop-blur-sm flex items-center justify-center p-8"
      onClick={onClose}
    >
      <button
        className="absolute top-4 right-4 text-white/60 hover:text-white text-3xl"
        onClick={onClose}
      >
        ×
      </button>
      <img
        src={imageUrl}
        alt={creative.sub_angle}
        className="max-w-full max-h-[85vh] object-contain rounded-lg shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      />
      <div className="absolute bottom-8 text-center text-white">
        <p className="font-semibold">{creative.sub_angle}</p>
        <p className="text-sm text-white/60">
          {creative.angle} — {creative.format}
        </p>
      </div>
    </div>
  );
}
