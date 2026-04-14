import { Creative, getImageUrl } from "@/components/CreativeCard";

export type MetaVariable = {
  id: string;
  brand_id: string;
  key: string;
  value: string;
};

export type MetaTemplate = {
  id: string;
  brand_id: string;
  name: string;
  template_string: string;
  is_default: boolean;
};

// ---------------------------------------------------------------------------
// Template rendering
// ---------------------------------------------------------------------------

/** Convert a raw value to an ad-name-safe token: lowercase, hyphens, no spaces. */
function slug(v: string): string {
  return v
    .toLowerCase()
    .replace(/ä/g, "ae")
    .replace(/ö/g, "oe")
    .replace(/ü/g, "ue")
    .replace(/ß/g, "ss")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function yyyymmdd(iso: string | null | undefined): string {
  const d = iso ? new Date(iso) : new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}${m}${day}`;
}

/**
 * Build the system variables that are derived from a creative row. These are
 * always available in templates — user-defined variables can override by key
 * except for the reserved keys below.
 */
export function systemVars(creative: Creative): Record<string, string> {
  const fmt = (creative.format || "").replace(":", "x");
  return {
    angle: slug(creative.angle || ""),
    sub_angle: slug(creative.sub_angle || ""),
    format: fmt,
    format_raw: creative.format || "",
    variant: String(creative.variant || 1),
    creative_id: creative.id.slice(0, 8),
    date: yyyymmdd(null),
    approved_date: yyyymmdd(creative.approved_at),
    created_date: yyyymmdd(creative.created_at),
  };
}

/**
 * Render a template string with {{key}} placeholders. User variables take
 * precedence over system variables — except for the reserved system keys
 * (angle, sub_angle, format, variant, creative_id, date, approved_date,
 * created_date) which always win, so a user can't accidentally shadow them.
 */
export function renderTemplate(
  template: string,
  creative: Creative,
  variables: MetaVariable[]
): string {
  const sys = systemVars(creative);
  const reserved = new Set(Object.keys(sys));
  const userMap: Record<string, string> = {};
  for (const v of variables) {
    if (!reserved.has(v.key)) {
      userMap[v.key] = v.value;
    }
  }
  const merged = { ...userMap, ...sys };
  return template.replace(/\{\{([\w-]+)\}\}/g, (_match, key) => {
    const val = merged[key];
    return val != null ? val : `{{${key}}}`;
  });
}

/**
 * Find all {{variable}} tokens in a template and return them. Useful for
 * autocomplete and showing which variables the user needs to define.
 */
export function extractVariableKeys(template: string): string[] {
  const matches = template.match(/\{\{([\w-]+)\}\}/g) || [];
  const keys = matches.map((m) => m.slice(2, -2));
  return [...new Set(keys)];
}

// ---------------------------------------------------------------------------
// CSV export
// ---------------------------------------------------------------------------

function csvEscape(v: unknown): string {
  const s = v == null ? "" : String(v);
  if (/[",\n\r]/.test(s)) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

const CSV_HEADERS = [
  "Ad Name",
  "Campaign",
  "Ad Set",
  "Angle",
  "Sub-Angle",
  "Format",
  "Primary Text",
  "Headline 1",
  "Headline 2",
  "Headline 3",
  "Headline 4",
  "Headline 5",
  "Description",
  "CTA",
  "Image URL",
  "Destination URL",
  "Ready",
] as const;

function rowFor(c: Creative): string[] {
  const headlines = c.headlines || [];
  return [
    c.meta_ad_name || "",
    c.meta_campaign || "",
    c.meta_ad_set || "",
    c.angle || "",
    c.sub_angle || "",
    c.format || "",
    c.primary_text || "",
    headlines[0] || "",
    headlines[1] || "",
    headlines[2] || "",
    headlines[3] || "",
    headlines[4] || "",
    c.description || "",
    c.cta || "",
    getImageUrl(c) || "",
    c.meta_destination_url || "",
    c.meta_ready ? "yes" : "no",
  ];
}

export function creativesToCsv(creatives: Creative[]): string {
  const lines = [
    CSV_HEADERS.map(csvEscape).join(","),
    ...creatives.map((c) => rowFor(c).map(csvEscape).join(",")),
  ];
  return lines.join("\n");
}

export function downloadCsv(creatives: Creative[], filename?: string): void {
  const csv = creativesToCsv(creatives);
  // Prefix BOM so Excel renders UTF-8 umlauts correctly.
  const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const date = new Date().toISOString().slice(0, 10);
  a.href = url;
  a.download = filename || `meta-upload-${date}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
