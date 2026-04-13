"use client";

import { useEffect, useState } from "react";
import { Creative, getImageUrl, downloadCreative } from "./CreativeCard";
import { supabase } from "@/lib/supabase";

type ImageOverlayProps = {
  creative: Creative | null;
  onClose: () => void;
};

const PIXEL_SIZES: Record<string, string> = {
  "4:5": "1440 × 1800 px",
  "9:16": "1440 × 2560 px",
  "1:1": "1440 × 1440 px",
  "16:9": "2560 × 1440 px",
};

const CTA_OPTIONS = [
  "Jetzt kaufen",
  "Mehr erfahren",
  "Angebot sichern",
  "Mehr ansehen",
  "Jetzt bestellen",
  "Registrieren",
];

const HEADLINE_LIMIT = 40;
const DESCRIPTION_LIMIT = 30;
const PRIMARY_TEXT_LIMIT = 500;

// ---------------------------------------------------------------------------
// Supabase writer
// ---------------------------------------------------------------------------

async function updateCreativeField(
  creativeId: string,
  field: string,
  value: string | string[] | null
) {
  const { error } = await supabase
    .from("creatives")
    .update({ [field]: value })
    .eq("id", creativeId);
  if (error) throw error;
}

// ---------------------------------------------------------------------------
// Copy-to-clipboard
// ---------------------------------------------------------------------------

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={async (e) => {
        e.stopPropagation();
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
      className="shrink-0 text-[10px] text-white/40 hover:text-white transition-colors px-2 py-1 rounded-md hover:bg-white/10"
      title="In Zwischenablage kopieren"
    >
      {copied ? "✓" : "copy"}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Editable text field (single-line or multiline)
// ---------------------------------------------------------------------------

type SaveState = "idle" | "saving" | "saved" | "error";

function EditableField({
  value,
  onCommit,
  multiline,
  placeholder,
  maxLength,
  rows = 4,
}: {
  value: string | null;
  onCommit: (next: string) => Promise<void>;
  multiline?: boolean;
  placeholder?: string;
  maxLength?: number;
  rows?: number;
}) {
  const [draft, setDraft] = useState(value ?? "");
  const [state, setState] = useState<SaveState>("idle");
  const [editing, setEditing] = useState(false);

  // Sync draft when external value changes (realtime updates), but only if not currently editing
  useEffect(() => {
    if (!editing) setDraft(value ?? "");
  }, [value, editing]);

  async function commit() {
    setEditing(false);
    if (draft === (value ?? "")) {
      setState("idle");
      return;
    }
    setState("saving");
    try {
      await onCommit(draft);
      setState("saved");
      setTimeout(() => setState("idle"), 1200);
    } catch (e) {
      console.error("save failed", e);
      setState("error");
      setTimeout(() => setState("idle"), 2500);
    }
  }

  const common = {
    value: draft,
    onChange: (e: React.ChangeEvent<HTMLTextAreaElement | HTMLInputElement>) =>
      setDraft(e.target.value),
    onFocus: () => setEditing(true),
    onBlur: commit,
    placeholder,
    maxLength,
    className:
      "w-full bg-white/5 hover:bg-white/10 focus:bg-white/10 border border-transparent focus:border-white/20 rounded-lg px-3 py-2 text-sm text-white/90 placeholder:text-white/20 outline-none transition-colors resize-none font-sans",
  };

  return (
    <div className="relative">
      {multiline ? (
        <textarea {...common} rows={rows} />
      ) : (
        <input type="text" {...common} />
      )}
      <div className="flex items-center justify-between mt-1 px-1">
        <div className="text-[10px] text-white/30 font-mono">
          {maxLength ? `${draft.length} / ${maxLength}` : `${draft.length} chars`}
        </div>
        <div className="text-[10px] font-mono">
          {state === "saving" && <span className="text-white/40">speichert…</span>}
          {state === "saved" && <span className="text-emerald-400">✓ gespeichert</span>}
          {state === "error" && <span className="text-red-400">✗ Fehler</span>}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Editable headlines list
// ---------------------------------------------------------------------------

function EditableHeadlines({
  headlines,
  onCommit,
}: {
  headlines: string[] | null;
  onCommit: (next: string[]) => Promise<void>;
}) {
  const list = headlines ?? [];
  const [drafts, setDrafts] = useState<string[]>(list);
  const [editingIdx, setEditingIdx] = useState<number | null>(null);
  const [state, setState] = useState<SaveState>("idle");

  useEffect(() => {
    if (editingIdx === null) setDrafts(headlines ?? []);
  }, [headlines, editingIdx]);

  async function persist(next: string[]) {
    setState("saving");
    try {
      await onCommit(next);
      setState("saved");
      setTimeout(() => setState("idle"), 1200);
    } catch (e) {
      console.error("save failed", e);
      setState("error");
      setTimeout(() => setState("idle"), 2500);
    }
  }

  async function commitAt(i: number) {
    setEditingIdx(null);
    const next = [...drafts];
    if ((next[i] ?? "") === (list[i] ?? "")) return;
    await persist(next);
  }

  async function remove(i: number) {
    const next = drafts.filter((_, idx) => idx !== i);
    setDrafts(next);
    await persist(next);
  }

  async function add() {
    const next = [...drafts, ""];
    setDrafts(next);
    setEditingIdx(next.length - 1);
  }

  return (
    <div className="space-y-1.5">
      {drafts.map((h, i) => (
        <div
          key={i}
          className="flex items-center gap-2 bg-white/5 rounded-lg pl-3 pr-1 py-1.5"
        >
          <span className="text-[10px] text-white/30 font-mono shrink-0 w-3">
            {i + 1}
          </span>
          <input
            type="text"
            value={h}
            maxLength={HEADLINE_LIMIT}
            onChange={(e) => {
              const next = [...drafts];
              next[i] = e.target.value;
              setDrafts(next);
            }}
            onFocus={() => setEditingIdx(i)}
            onBlur={() => commitAt(i)}
            className="flex-1 bg-transparent text-sm text-white/90 outline-none focus:bg-white/5 rounded px-1 py-0.5"
            placeholder="Headline eingeben…"
          />
          <span className="text-[10px] text-white/30 font-mono shrink-0 w-10 text-right">
            {h.length}/{HEADLINE_LIMIT}
          </span>
          <CopyButton text={h} />
          <button
            onClick={() => remove(i)}
            className="text-white/30 hover:text-red-400 transition-colors px-2 py-1 rounded-md hover:bg-white/10"
            title="Entfernen"
          >
            ×
          </button>
        </div>
      ))}
      <div className="flex items-center justify-between pt-1">
        <button
          onClick={add}
          className="text-[11px] text-white/50 hover:text-white transition-colors px-2 py-1 rounded-md hover:bg-white/10"
        >
          + Headline hinzufügen
        </button>
        <div className="text-[10px] font-mono">
          {state === "saving" && <span className="text-white/40">speichert…</span>}
          {state === "saved" && <span className="text-emerald-400">✓ gespeichert</span>}
          {state === "error" && <span className="text-red-400">✗ Fehler</span>}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// CTA dropdown
// ---------------------------------------------------------------------------

function EditableCTA({
  value,
  onCommit,
}: {
  value: string | null;
  onCommit: (next: string) => Promise<void>;
}) {
  const [draft, setDraft] = useState(value ?? "");
  const [state, setState] = useState<SaveState>("idle");

  useEffect(() => setDraft(value ?? ""), [value]);

  async function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const next = e.target.value;
    setDraft(next);
    setState("saving");
    try {
      await onCommit(next);
      setState("saved");
      setTimeout(() => setState("idle"), 1200);
    } catch {
      setState("error");
      setTimeout(() => setState("idle"), 2500);
    }
  }

  return (
    <div className="flex items-center gap-2">
      <select
        value={draft}
        onChange={handleChange}
        className="bg-white/5 hover:bg-white/10 border border-transparent hover:border-white/20 rounded-lg px-3 py-2 text-sm text-white/90 outline-none cursor-pointer"
      >
        <option value="" disabled className="bg-[#0f0f11]">
          — CTA wählen —
        </option>
        {CTA_OPTIONS.map((c) => (
          <option key={c} value={c} className="bg-[#0f0f11]">
            {c}
          </option>
        ))}
      </select>
      <div className="text-[10px] font-mono">
        {state === "saving" && <span className="text-white/40">speichert…</span>}
        {state === "saved" && <span className="text-emerald-400">✓</span>}
        {state === "error" && <span className="text-red-400">✗</span>}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section wrapper
// ---------------------------------------------------------------------------

function Section({
  title,
  hint,
  children,
  copyText,
}: {
  title: string;
  hint?: string;
  children: React.ReactNode;
  copyText?: string;
}) {
  return (
    <div className="py-4 border-t border-white/10 first:border-t-0 first:pt-0">
      <div className="flex items-center justify-between mb-2">
        <div>
          <div className="text-[10px] text-white/40 uppercase tracking-wider font-semibold">
            {title}
          </div>
          {hint && <div className="text-[10px] text-white/25 mt-0.5">{hint}</div>}
        </div>
        {copyText && <CopyButton text={copyText} />}
      </div>
      {children}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main overlay
// ---------------------------------------------------------------------------

export default function ImageOverlay({ creative, onClose }: ImageOverlayProps) {
  const [regenerating, setRegenerating] = useState(false);
  const [regenError, setRegenError] = useState<string | null>(null);

  if (!creative) return null;
  const imageUrl = getImageUrl(creative);
  if (!imageUrl) return null;

  const pixelSize = PIXEL_SIZES[creative.format] || creative.format;
  const hasCopy =
    !!creative.primary_text || !!(creative.headlines && creative.headlines.length);

  async function regenerateCopy() {
    if (!creative) return;
    setRegenerating(true);
    setRegenError(null);
    try {
      const resp = await fetch("/api/briefing/regenerate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ creative_id: creative.id }),
      });
      if (!resp.ok) {
        const txt = await resp.text();
        throw new Error(txt || `HTTP ${resp.status}`);
      }
    } catch (e) {
      setRegenError(e instanceof Error ? e.message : String(e));
    } finally {
      setRegenerating(false);
    }
  }

  const save = (field: string) => (value: string | string[]) =>
    updateCreativeField(creative.id, field, value);

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/95 backdrop-blur-md flex"
      onClick={onClose}
    >
      <button
        className="absolute top-4 right-4 z-10 w-10 h-10 flex items-center justify-center rounded-full bg-white/10 text-white/60 hover:text-white hover:bg-white/20 transition-colors text-xl"
        onClick={onClose}
      >
        ×
      </button>

      {/* Image side */}
      <div
        className="flex-1 flex items-center justify-center p-8"
        onClick={(e) => e.stopPropagation()}
      >
        <img
          src={imageUrl}
          alt={creative.sub_angle}
          className="max-h-[90vh] max-w-full object-contain rounded-xl shadow-2xl"
        />
      </div>

      {/* Briefing + copy panel */}
      <aside
        className="hidden lg:flex w-[460px] shrink-0 flex-col bg-[#0f0f11] border-l border-white/10 overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 pb-4 border-b border-white/10">
          <div className="text-[10px] text-white/40 uppercase tracking-wider font-semibold">
            {creative.angle}
          </div>
          <h2 className="text-white font-semibold text-lg mt-0.5 leading-tight">
            {creative.sub_angle}
          </h2>
          {creative.hook_text && (
            <p className="text-white/60 text-sm mt-2 italic leading-relaxed">
              &ldquo;{creative.hook_text}&rdquo;
            </p>
          )}
          <div className="flex items-center gap-2 text-[11px] text-white/40 mt-3 font-mono">
            <span>{creative.format}</span>
            <span>·</span>
            <span>{pixelSize}</span>
          </div>
          <div className="mt-4 flex items-center gap-2">
            <button
              onClick={() => downloadCreative(creative)}
              className="flex-1 text-xs font-semibold bg-white text-black py-2 rounded-lg hover:bg-white/90 transition-colors"
            >
              Download
            </button>
            <button
              onClick={regenerateCopy}
              disabled={regenerating}
              className="flex-1 text-xs font-semibold bg-white/10 text-white py-2 rounded-lg hover:bg-white/20 transition-colors disabled:opacity-50"
              title="Briefing + Meta Copy neu generieren"
            >
              {regenerating
                ? "Läuft…"
                : hasCopy
                ? "↻ Regenerate"
                : "Generate Copy"}
            </button>
          </div>
          {regenError && (
            <div className="mt-2 text-[11px] text-red-400 leading-tight">
              {regenError}
            </div>
          )}
        </div>

        <div className="px-6 py-4">
          <div className="text-[10px] text-white/40 uppercase tracking-wider font-semibold mb-3">
            Ad Copy
          </div>

          <Section
            title="Primary Text"
            hint="Meta Caption — ~125 Zeichen im Feed sichtbar, Rest hinter &ldquo;Mehr ansehen&rdquo;"
            copyText={creative.primary_text ?? undefined}
          >
            <EditableField
              value={creative.primary_text}
              onCommit={save("primary_text")}
              multiline
              rows={5}
              maxLength={PRIMARY_TEXT_LIMIT}
              placeholder="Primary Text eingeben…"
            />
          </Section>

          <Section title={`Headlines — max ${HEADLINE_LIMIT} Zeichen je Variante`}>
            <EditableHeadlines
              headlines={creative.headlines}
              onCommit={save("headlines") as (v: string[]) => Promise<void>}
            />
          </Section>

          <Section
            title={`Description — max ${DESCRIPTION_LIMIT} Zeichen`}
            hint="Meta Link Description"
            copyText={creative.description ?? undefined}
          >
            <EditableField
              value={creative.description}
              onCommit={save("description")}
              maxLength={DESCRIPTION_LIMIT}
              placeholder="Description eingeben…"
            />
          </Section>

          <Section title="CTA">
            <EditableCTA value={creative.cta} onCommit={save("cta")} />
          </Section>
        </div>

        <div className="px-6 pb-6 pt-2 border-t border-white/10">
          <div className="text-[10px] text-white/40 uppercase tracking-wider font-semibold mb-3">
            Briefing Details
          </div>

          <Section
            title="Briefing Rationale"
            hint="Warum performt dieses Creative? Angle + Metapher-Logik."
            copyText={creative.briefing_rationale ?? undefined}
          >
            <EditableField
              value={creative.briefing_rationale}
              onCommit={save("briefing_rationale")}
              multiline
              rows={4}
              placeholder="Rationale…"
            />
          </Section>

          <Section
            title="Target Audience"
            hint="Demografie + psychografischer Trigger"
            copyText={creative.target_audience ?? undefined}
          >
            <EditableField
              value={creative.target_audience}
              onCommit={save("target_audience")}
              multiline
              rows={3}
              placeholder="Zielgruppe…"
            />
          </Section>

          {creative.copy_generated_at && (
            <div className="pt-3 mt-2 border-t border-white/10 text-[10px] text-white/30 font-mono">
              Copy generated:{" "}
              {new Date(creative.copy_generated_at).toLocaleString("de-CH")}
            </div>
          )}
        </div>
      </aside>

      {/* Mobile fallback */}
      <div className="lg:hidden absolute bottom-6 left-6 right-6 text-center text-white">
        <p className="font-semibold">{creative.sub_angle}</p>
        <p className="text-sm text-white/60">
          {creative.angle} — {creative.format}
        </p>
      </div>
    </div>
  );
}
