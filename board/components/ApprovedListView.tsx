"use client";

import { useEffect, useRef, useState } from "react";
import { Creative, getImageUrl, ANGLE_EMOJI } from "./CreativeCard";

type Props = {
  creatives: Creative[];
  selected: Set<string>;
  onToggleSelect: (id: string) => void;
  onToggleSelectAll: (all: boolean) => void;
  onFieldChange: (
    id: string,
    field: "meta_ad_name" | "meta_campaign" | "meta_ad_set" | "meta_destination_url",
    value: string
  ) => Promise<void>;
  onReadyChange: (id: string, ready: boolean) => Promise<void>;
  onOpenPreview: (creative: Creative) => void;
  onMarkLive: (id: string) => Promise<void>;
  onRevoke: (id: string) => Promise<void>;
  variableKeys: string[];
};

type CellField =
  | "meta_ad_name"
  | "meta_campaign"
  | "meta_ad_set"
  | "meta_destination_url";

// ---------------------------------------------------------------------------
// Editable cell with auto-save + variable-aware autocomplete ({{ trigger)
// ---------------------------------------------------------------------------

function EditableCell({
  value,
  onCommit,
  placeholder,
  variableKeys,
  minWidth,
}: {
  value: string;
  onCommit: (next: string) => Promise<void>;
  placeholder?: string;
  variableKeys: string[];
  minWidth?: number;
}) {
  const [draft, setDraft] = useState(value ?? "");
  const [editing, setEditing] = useState(false);
  const [saved, setSaved] = useState(false);
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [autocompleteQuery, setAutocompleteQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!editing) setDraft(value ?? "");
  }, [value, editing]);

  async function commit() {
    setEditing(false);
    setShowAutocomplete(false);
    if ((draft ?? "") === (value ?? "")) return;
    try {
      await onCommit(draft);
      setSaved(true);
      setTimeout(() => setSaved(false), 900);
    } catch {
      // noop — revert
      setDraft(value ?? "");
    }
  }

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const next = e.target.value;
    setDraft(next);

    // Autocomplete when user types "{{"
    const cursor = e.target.selectionStart ?? next.length;
    const before = next.slice(0, cursor);
    const match = before.match(/\{\{([\w-]*)$/);
    if (match) {
      setShowAutocomplete(true);
      setAutocompleteQuery(match[1]);
    } else {
      setShowAutocomplete(false);
    }
  }

  function insertVariable(key: string) {
    if (!inputRef.current) return;
    const el = inputRef.current;
    const cursor = el.selectionStart ?? draft.length;
    const before = draft.slice(0, cursor).replace(/\{\{[\w-]*$/, "");
    const after = draft.slice(cursor);
    const next = `${before}{{${key}}}${after}`;
    setDraft(next);
    setShowAutocomplete(false);
    setTimeout(() => {
      const pos = (before + `{{${key}}}`).length;
      el.focus();
      el.setSelectionRange(pos, pos);
    }, 0);
  }

  const filteredKeys = variableKeys.filter((k) =>
    k.toLowerCase().includes(autocompleteQuery.toLowerCase())
  );

  return (
    <div className="relative" style={{ minWidth }}>
      <input
        ref={inputRef}
        type="text"
        value={draft}
        onChange={handleChange}
        onFocus={() => setEditing(true)}
        onBlur={() => setTimeout(commit, 150)} // delay so click on autocomplete works
        placeholder={placeholder}
        className="w-full bg-transparent hover:bg-background focus:bg-background border border-transparent focus:border-border rounded px-2 py-1 text-[12px] outline-none transition-colors"
      />
      {saved && (
        <span className="absolute -right-5 top-1/2 -translate-y-1/2 text-[9px] text-emerald-500 font-mono">
          ✓
        </span>
      )}
      {showAutocomplete && filteredKeys.length > 0 && (
        <div className="absolute z-50 mt-1 left-0 bg-surface border border-border rounded-lg shadow-lg py-1 min-w-[180px] max-h-60 overflow-y-auto">
          <div className="px-3 py-1 text-[9px] text-muted uppercase tracking-wider">
            Variables
          </div>
          {filteredKeys.map((k) => (
            <button
              key={k}
              onMouseDown={(e) => {
                e.preventDefault();
                insertVariable(k);
              }}
              className="block w-full text-left px-3 py-1 text-[12px] font-mono text-foreground hover:bg-background transition-colors"
            >
              {`{{${k}}}`}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main list view
// ---------------------------------------------------------------------------

export default function ApprovedListView({
  creatives,
  selected,
  onToggleSelect,
  onToggleSelectAll,
  onFieldChange,
  onReadyChange,
  onOpenPreview,
  onMarkLive,
  onRevoke,
  variableKeys,
}: Props) {
  const allSelected = creatives.length > 0 && selected.size === creatives.length;
  const someSelected = selected.size > 0 && !allSelected;

  return (
    <div className="bg-surface border border-border rounded-xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-background border-b border-border">
            <tr className="text-[10px] text-muted uppercase tracking-wider">
              <th className="w-10 px-3 py-2.5 text-left">
                <input
                  type="checkbox"
                  checked={allSelected}
                  ref={(el) => {
                    if (el) el.indeterminate = someSelected;
                  }}
                  onChange={(e) => onToggleSelectAll(e.target.checked)}
                  className="cursor-pointer"
                />
              </th>
              <th className="w-14 px-2 py-2.5 text-left">Thumb</th>
              <th className="px-2 py-2.5 text-left">Angle</th>
              <th className="w-16 px-2 py-2.5 text-left">Format</th>
              <th className="px-2 py-2.5 text-left min-w-[240px]">Meta Ad Name</th>
              <th className="px-2 py-2.5 text-left min-w-[180px]">Campaign</th>
              <th className="px-2 py-2.5 text-left min-w-[180px]">Ad Set</th>
              <th className="px-2 py-2.5 text-left min-w-[220px]">Dest URL</th>
              <th className="w-16 px-2 py-2.5 text-center">Ready</th>
              <th className="w-32 px-2 py-2.5 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {creatives.map((c) => {
              const imageUrl = getImageUrl(c);
              const isSelected = selected.has(c.id);
              const isReady = !!c.meta_ready;
              return (
                <tr
                  key={c.id}
                  className={`border-b border-border/50 transition-colors ${
                    isSelected
                      ? "bg-primary/5"
                      : isReady
                      ? "bg-emerald-500/5"
                      : "hover:bg-background/50"
                  }`}
                >
                  <td className="px-3 py-2">
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => onToggleSelect(c.id)}
                      className="cursor-pointer"
                    />
                  </td>
                  <td className="px-2 py-2">
                    {imageUrl ? (
                      <button
                        onClick={() => onOpenPreview(c)}
                        className="block w-10 h-10 rounded-md overflow-hidden bg-background border border-border hover:border-primary/50 transition-colors"
                        title="Preview"
                      >
                        <img
                          src={imageUrl}
                          alt={c.sub_angle}
                          className="w-full h-full object-cover"
                        />
                      </button>
                    ) : (
                      <div className="w-10 h-10 rounded-md bg-background border border-border" />
                    )}
                  </td>
                  <td className="px-2 py-2">
                    <div className="flex items-center gap-1.5">
                      <span>{ANGLE_EMOJI[c.angle] ?? "•"}</span>
                      <div className="min-w-0">
                        <div className="text-[12px] font-medium text-foreground truncate max-w-[140px]">
                          {c.angle}
                        </div>
                        {c.sub_angle && (
                          <div className="text-[10px] text-muted truncate max-w-[140px]">
                            {c.sub_angle}
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-2 py-2">
                    <span className="text-[10px] font-mono bg-background border border-border px-1.5 py-0.5 rounded">
                      {c.format}
                    </span>
                  </td>
                  <td className="px-2 py-2">
                    <EditableCell
                      value={c.meta_ad_name ?? ""}
                      onCommit={(v) => onFieldChange(c.id, "meta_ad_name", v)}
                      placeholder="Ad name…"
                      variableKeys={variableKeys}
                    />
                  </td>
                  <td className="px-2 py-2">
                    <EditableCell
                      value={c.meta_campaign ?? ""}
                      onCommit={(v) => onFieldChange(c.id, "meta_campaign", v)}
                      placeholder="Campaign…"
                      variableKeys={variableKeys}
                    />
                  </td>
                  <td className="px-2 py-2">
                    <EditableCell
                      value={c.meta_ad_set ?? ""}
                      onCommit={(v) => onFieldChange(c.id, "meta_ad_set", v)}
                      placeholder="Ad set…"
                      variableKeys={variableKeys}
                    />
                  </td>
                  <td className="px-2 py-2">
                    <EditableCell
                      value={c.meta_destination_url ?? ""}
                      onCommit={(v) =>
                        onFieldChange(c.id, "meta_destination_url", v)
                      }
                      placeholder="https://…"
                      variableKeys={variableKeys}
                    />
                  </td>
                  <td className="px-2 py-2 text-center">
                    <input
                      type="checkbox"
                      checked={isReady}
                      onChange={(e) => onReadyChange(c.id, e.target.checked)}
                      className="cursor-pointer w-4 h-4 accent-emerald-500"
                    />
                  </td>
                  <td className="px-2 py-2">
                    <div className="flex items-center justify-end gap-1">
                      {c.approval_status === "approved" ? (
                        <button
                          onClick={() => onMarkLive(c.id)}
                          className="text-[10px] font-semibold text-blue-600 hover:text-blue-700 px-2 py-1 rounded hover:bg-blue-50 transition-colors"
                          title="Mark as live in Meta"
                        >
                          Live
                        </button>
                      ) : (
                        <span className="flex items-center gap-0.5 text-[10px] font-semibold text-blue-600">
                          <span className="w-1 h-1 bg-blue-500 rounded-full" />
                          Live
                        </span>
                      )}
                      <button
                        onClick={() => onRevoke(c.id)}
                        className="text-[10px] text-muted hover:text-red-500 px-2 py-1 rounded hover:bg-red-50 transition-colors"
                        title="Back to draft"
                      >
                        ↶
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
