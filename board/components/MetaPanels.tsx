"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { MetaVariable, MetaTemplate, extractVariableKeys } from "@/lib/meta-upload";

// ---------------------------------------------------------------------------
// Variables Panel
// ---------------------------------------------------------------------------

export function VariablesPanel({
  brandId,
  open,
  onClose,
  onChanged,
  reservedKeys,
}: {
  brandId: string;
  open: boolean;
  onClose: () => void;
  onChanged: () => void;
  reservedKeys: string[];
}) {
  const [variables, setVariables] = useState<MetaVariable[]>([]);
  const [newKey, setNewKey] = useState("");
  const [newValue, setNewValue] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    load();
  }, [open, brandId]);

  async function load() {
    const { data } = await supabase
      .from("meta_variables")
      .select("*")
      .eq("brand_id", brandId)
      .order("key");
    setVariables((data as MetaVariable[]) ?? []);
  }

  async function addVariable() {
    setError(null);
    const key = newKey.trim();
    const value = newValue.trim();
    if (!key || !value) return;
    if (reservedKeys.includes(key)) {
      setError(`"${key}" ist eine System-Variable und kann nicht überschrieben werden`);
      return;
    }
    if (!/^[a-z][a-z0-9_]*$/.test(key)) {
      setError("Key darf nur kleinbuchstaben, zahlen und _ enthalten, mit buchstabe anfangen");
      return;
    }
    const { error: err } = await supabase
      .from("meta_variables")
      .insert({ brand_id: brandId, key, value });
    if (err) {
      setError(err.message);
      return;
    }
    setNewKey("");
    setNewValue("");
    await load();
    onChanged();
  }

  async function updateValue(id: string, value: string) {
    await supabase.from("meta_variables").update({ value }).eq("id", id);
    onChanged();
  }

  async function removeVariable(id: string) {
    await supabase.from("meta_variables").delete().eq("id", id);
    await load();
    onChanged();
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/70 backdrop-blur-sm flex items-center justify-center p-6"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl max-h-[85vh] bg-surface border border-border rounded-2xl overflow-y-auto shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-surface border-b border-border p-5 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-foreground">Variables</h2>
            <p className="text-xs text-muted mt-0.5">
              Wiederverwendbare Tokens für Naming und Campaign-Felder
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-background text-muted text-lg"
          >
            ×
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* System vars (readonly reference) */}
          <div>
            <div className="text-[10px] uppercase tracking-wider font-semibold text-muted mb-1.5">
              System-Variablen (automatisch aus Creative)
            </div>
            <div className="flex flex-wrap gap-1">
              {reservedKeys.map((k) => (
                <span
                  key={k}
                  className="text-[11px] font-mono bg-background text-muted px-2 py-0.5 rounded-md"
                >
                  {`{{${k}}}`}
                </span>
              ))}
            </div>
          </div>

          {/* User vars */}
          <div>
            <div className="text-[10px] uppercase tracking-wider font-semibold text-muted mb-2">
              Deine Variablen
            </div>
            {variables.length === 0 ? (
              <div className="text-xs text-muted italic py-2">Noch keine Variablen definiert.</div>
            ) : (
              <div className="space-y-1.5">
                {variables.map((v) => (
                  <div
                    key={v.id}
                    className="flex items-center gap-2 bg-background rounded-lg px-3 py-2"
                  >
                    <code className="text-[11px] font-mono text-primary shrink-0 w-32 truncate">
                      {`{{${v.key}}}`}
                    </code>
                    <input
                      type="text"
                      defaultValue={v.value}
                      onBlur={(e) => {
                        if (e.target.value !== v.value) updateValue(v.id, e.target.value);
                      }}
                      className="flex-1 bg-transparent text-xs text-foreground outline-none border border-transparent focus:border-border rounded px-2 py-1"
                    />
                    <button
                      onClick={() => removeVariable(v.id)}
                      className="text-muted hover:text-red-500 text-sm px-2"
                      title="Remove"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Add new */}
          <div>
            <div className="text-[10px] uppercase tracking-wider font-semibold text-muted mb-2">
              Neue Variable
            </div>
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={newKey}
                onChange={(e) => setNewKey(e.target.value.toLowerCase())}
                placeholder="key (z.B. campaign)"
                className="w-40 bg-background border border-border rounded-lg px-3 py-2 text-xs outline-none focus:border-primary"
              />
              <input
                type="text"
                value={newValue}
                onChange={(e) => setNewValue(e.target.value)}
                placeholder="value"
                className="flex-1 bg-background border border-border rounded-lg px-3 py-2 text-xs outline-none focus:border-primary"
              />
              <button
                onClick={addVariable}
                disabled={!newKey.trim() || !newValue.trim()}
                className="text-xs font-semibold bg-primary text-white px-4 py-2 rounded-lg hover:bg-primary/90 disabled:opacity-40 transition-colors"
              >
                Add
              </button>
            </div>
            {error && (
              <div className="mt-2 text-[11px] text-red-500">{error}</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Templates Panel
// ---------------------------------------------------------------------------

export function TemplatesPanel({
  brandId,
  open,
  onClose,
  onChanged,
  availableKeys,
}: {
  brandId: string;
  open: boolean;
  onClose: () => void;
  onChanged: () => void;
  availableKeys: string[];
}) {
  const [templates, setTemplates] = useState<MetaTemplate[]>([]);
  const [newName, setNewName] = useState("");
  const [newTemplate, setNewTemplate] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    load();
  }, [open, brandId]);

  async function load() {
    const { data } = await supabase
      .from("meta_templates")
      .select("*")
      .eq("brand_id", brandId)
      .order("is_default", { ascending: false })
      .order("name");
    setTemplates((data as MetaTemplate[]) ?? []);
  }

  async function addTemplate() {
    setError(null);
    const name = newName.trim();
    const template_string = newTemplate.trim();
    if (!name || !template_string) return;
    const { error: err } = await supabase
      .from("meta_templates")
      .insert({ brand_id: brandId, name, template_string });
    if (err) {
      setError(err.message);
      return;
    }
    setNewName("");
    setNewTemplate("");
    await load();
    onChanged();
  }

  async function updateTemplate(id: string, field: "name" | "template_string", value: string) {
    await supabase.from("meta_templates").update({ [field]: value }).eq("id", id);
    onChanged();
  }

  async function setDefault(id: string) {
    // Unset all, then set the selected one
    await supabase
      .from("meta_templates")
      .update({ is_default: false })
      .eq("brand_id", brandId);
    await supabase.from("meta_templates").update({ is_default: true }).eq("id", id);
    await load();
    onChanged();
  }

  async function removeTemplate(id: string) {
    await supabase.from("meta_templates").delete().eq("id", id);
    await load();
    onChanged();
  }

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/70 backdrop-blur-sm flex items-center justify-center p-6"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl max-h-[85vh] bg-surface border border-border rounded-2xl overflow-y-auto shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-surface border-b border-border p-5 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-foreground">Naming Templates</h2>
            <p className="text-xs text-muted mt-0.5">
              Muster für auto-generierte Ad-Namen. Nutze {"{{ }}"} Tokens.
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-background text-muted text-lg"
          >
            ×
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* Existing templates */}
          <div className="space-y-2">
            {templates.length === 0 ? (
              <div className="text-xs text-muted italic">Noch keine Templates.</div>
            ) : (
              templates.map((t) => {
                const keys = extractVariableKeys(t.template_string);
                const missing = keys.filter((k) => !availableKeys.includes(k));
                return (
                  <div
                    key={t.id}
                    className={`rounded-lg border p-3 ${
                      t.is_default
                        ? "border-primary/40 bg-primary/5"
                        : "border-border bg-background"
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-2">
                      <input
                        type="text"
                        defaultValue={t.name}
                        onBlur={(e) => {
                          if (e.target.value !== t.name) updateTemplate(t.id, "name", e.target.value);
                        }}
                        className="flex-1 bg-transparent text-sm font-semibold text-foreground outline-none border border-transparent focus:border-border rounded px-2 py-1"
                      />
                      {t.is_default ? (
                        <span className="text-[10px] font-semibold text-primary bg-primary/10 px-2 py-0.5 rounded">
                          DEFAULT
                        </span>
                      ) : (
                        <button
                          onClick={() => setDefault(t.id)}
                          className="text-[10px] text-muted hover:text-primary px-2 py-0.5 rounded hover:bg-background transition-colors"
                        >
                          Set default
                        </button>
                      )}
                      <button
                        onClick={() => removeTemplate(t.id)}
                        className="text-muted hover:text-red-500 text-sm px-2"
                        title="Remove"
                      >
                        ×
                      </button>
                    </div>
                    <input
                      type="text"
                      defaultValue={t.template_string}
                      onBlur={(e) => {
                        if (e.target.value !== t.template_string)
                          updateTemplate(t.id, "template_string", e.target.value);
                      }}
                      className="w-full bg-surface border border-border rounded px-3 py-2 text-[12px] font-mono outline-none focus:border-primary"
                    />
                    {missing.length > 0 && (
                      <div className="mt-1.5 text-[10px] text-amber-500">
                        ⚠ Undefined vars: {missing.map((k) => `{{${k}}}`).join(", ")}
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>

          {/* Add new */}
          <div className="pt-3 border-t border-border">
            <div className="text-[10px] uppercase tracking-wider font-semibold text-muted mb-2">
              Neues Template
            </div>
            <div className="space-y-2">
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="Name (z.B. Spring Campaign Naming)"
                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-xs outline-none focus:border-primary"
              />
              <input
                type="text"
                value={newTemplate}
                onChange={(e) => setNewTemplate(e.target.value)}
                placeholder="ora_{{campaign}}_{{angle}}_{{format}}_v{{variant}}"
                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-[12px] font-mono outline-none focus:border-primary"
              />
              <div className="flex items-center justify-between">
                <div className="text-[10px] text-muted">
                  Verfügbare Variablen:{" "}
                  <span className="font-mono">
                    {availableKeys.slice(0, 6).map((k) => `{{${k}}}`).join(" ")}
                    {availableKeys.length > 6 ? "…" : ""}
                  </span>
                </div>
                <button
                  onClick={addTemplate}
                  disabled={!newName.trim() || !newTemplate.trim()}
                  className="text-xs font-semibold bg-primary text-white px-4 py-2 rounded-lg hover:bg-primary/90 disabled:opacity-40 transition-colors"
                >
                  Add
                </button>
              </div>
              {error && (
                <div className="text-[11px] text-red-500">{error}</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
