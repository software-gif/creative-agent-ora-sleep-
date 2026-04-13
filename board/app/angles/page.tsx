"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import { useBrand } from "@/lib/brand-context";
import { ANGLE_COLORS, ANGLE_EMOJI } from "@/components/CreativeCard";

type Angle = {
  id: string;
  key: string;
  name: string;
  type: string;
  data_point: string | null;
  priority: number;
  status: string;
  last_updated_at: string;
};

type AngleVariant = {
  id: string;
  angle_id: string;
  variant_type: "headline" | "hook";
  content: string;
  display_order: number;
  status: string;
};

type AngleWithVariants = Angle & {
  headlines: AngleVariant[];
  hooks: AngleVariant[];
  creative_count: number;
};

const TYPE_ORDER = [
  "Problem/Pain",
  "Benefit",
  "Proof",
  "Curiosity",
  "Education",
  "Story",
  "Offer",
];

export default function AnglesPage() {
  const { brandId, loading: brandLoading } = useBrand();
  const [angles, setAngles] = useState<AngleWithVariants[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    if (!brandId) return;
    load(brandId);
  }, [brandId]);

  async function load(bid: string) {
    setLoading(true);

    const [anglesRes, variantsRes, creativesRes] = await Promise.all([
      supabase
        .from("angles")
        .select("*")
        .eq("brand_id", bid)
        .eq("status", "active")
        .order("priority"),
      supabase
        .from("angle_variants")
        .select("*")
        .eq("status", "active")
        .order("display_order"),
      supabase
        .from("creatives")
        .select("angle")
        .eq("brand_id", bid),
    ]);

    if (anglesRes.error || !anglesRes.data) {
      setLoading(false);
      return;
    }

    const variantsByAngle = new Map<string, AngleVariant[]>();
    for (const v of variantsRes.data ?? []) {
      const list = variantsByAngle.get(v.angle_id) ?? [];
      list.push(v);
      variantsByAngle.set(v.angle_id, list);
    }

    const countsByKey = new Map<string, number>();
    for (const c of creativesRes.data ?? []) {
      if (!c.angle) continue;
      countsByKey.set(c.angle, (countsByKey.get(c.angle) ?? 0) + 1);
    }

    const withVariants: AngleWithVariants[] = anglesRes.data.map((a: Angle) => {
      const vs = variantsByAngle.get(a.id) ?? [];
      return {
        ...a,
        headlines: vs.filter((v) => v.variant_type === "headline"),
        hooks: vs.filter((v) => v.variant_type === "hook"),
        creative_count: countsByKey.get(a.key) ?? 0,
      };
    });

    setAngles(withVariants);
    setLoading(false);
  }

  const grouped = new Map<string, AngleWithVariants[]>();
  for (const a of angles) {
    const list = grouped.get(a.type) ?? [];
    list.push(a);
    grouped.set(a.type, list);
  }
  const orderedTypes = [
    ...TYPE_ORDER.filter((t) => grouped.has(t)),
    ...[...grouped.keys()].filter((t) => !TYPE_ORDER.includes(t)),
  ];

  if (brandLoading || loading) {
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

  if (angles.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-80 text-muted p-6">
        <p className="text-lg font-semibold text-foreground">Noch keine Angles</p>
        <p className="text-sm mt-2 max-w-md text-center">
          Führe{" "}
          <code className="bg-background px-1.5 py-0.5 rounded text-xs">
            python3 scripts/sync_to_board.py
          </code>{" "}
          im Creative-Generator-Ordner aus, um die bestehenden Angles aus{" "}
          <code className="bg-background px-1.5 py-0.5 rounded text-xs">
            angles.json
          </code>{" "}
          zu synchronisieren.
        </p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <div className="sticky top-[57px] z-40 bg-surface/95 backdrop-blur-sm border-b border-border px-6 py-2.5">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-sm font-semibold text-foreground">Angles</h1>
            <p className="text-[11px] text-muted">
              {angles.length} aktive Angles ·{" "}
              {angles.reduce((s, a) => s + a.creative_count, 0)} Creatives erstellt
            </p>
          </div>
          <div className="text-[10px] text-muted">
            Sag dem Agent &ldquo;erstell ein Creative für angle [key]&rdquo;
          </div>
        </div>
      </div>

      <main className="p-6 space-y-8">
        {orderedTypes.map((type) => {
          const items = grouped.get(type) ?? [];
          return (
            <section key={type}>
              <div className="flex items-center gap-2 mb-3">
                <span className="text-lg">{ANGLE_EMOJI[type] ?? "•"}</span>
                <h2
                  className={`text-xs font-semibold uppercase tracking-wider ${
                    ANGLE_COLORS[type] ?? "text-muted"
                  }`}
                >
                  {type}
                </h2>
                <span className="text-[10px] text-muted font-mono">
                  {items.length}
                </span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {items.map((a) => {
                  const isOpen = expanded === a.id;
                  return (
                    <div
                      key={a.id}
                      className="bg-surface border border-border rounded-xl overflow-hidden hover:border-primary/30 transition-colors"
                    >
                      <div className="p-4">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <div className="text-[9px] font-mono text-muted uppercase tracking-wider">
                              {a.key}
                            </div>
                            <h3 className="font-semibold text-foreground leading-tight mt-0.5">
                              {a.name}
                            </h3>
                          </div>
                          <span className="shrink-0 text-[10px] font-semibold bg-background text-muted px-2 py-1 rounded-md">
                            {a.creative_count} creative
                            {a.creative_count === 1 ? "" : "s"}
                          </span>
                        </div>

                        {a.data_point && (
                          <div className="mt-3 text-xs text-accent bg-accent/10 rounded-lg px-3 py-2 leading-relaxed">
                            {a.data_point}
                          </div>
                        )}

                        {a.headlines.length > 0 && (
                          <div className="mt-3">
                            <div className="text-[10px] text-muted uppercase tracking-wider font-semibold mb-1.5">
                              Headline-Varianten
                            </div>
                            <ul className="space-y-1">
                              {(isOpen ? a.headlines : a.headlines.slice(0, 3)).map(
                                (v) => (
                                  <li
                                    key={v.id}
                                    className="text-xs text-foreground bg-background rounded-md px-2.5 py-1.5 leading-snug"
                                  >
                                    {v.content}
                                  </li>
                                )
                              )}
                            </ul>
                          </div>
                        )}

                        {isOpen && a.hooks.length > 0 && (
                          <div className="mt-3">
                            <div className="text-[10px] text-muted uppercase tracking-wider font-semibold mb-1.5">
                              Hook-Varianten
                            </div>
                            <ul className="space-y-1">
                              {a.hooks.map((v) => (
                                <li
                                  key={v.id}
                                  className="text-xs text-muted italic bg-background rounded-md px-2.5 py-1.5 leading-snug"
                                >
                                  &ldquo;{v.content}&rdquo;
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {(a.headlines.length > 3 || a.hooks.length > 0) && (
                          <button
                            onClick={() => setExpanded(isOpen ? null : a.id)}
                            className="mt-3 text-[11px] text-primary hover:text-primary/80 font-medium"
                          >
                            {isOpen
                              ? "Weniger anzeigen"
                              : `Mehr anzeigen${
                                  a.hooks.length > 0
                                    ? ` (${a.hooks.length} Hooks)`
                                    : ""
                                }`}
                          </button>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          );
        })}
      </main>
    </div>
  );
}
