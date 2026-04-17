"use client";

const PRODUCTS = [
  {
    slug: "ora-ultra-matratze",
    name: "Ora Ultra Matratze",
    tagline: "Der erholsamste Schlaf deines Lebens – ab Nacht eins.",
    type: "Matratze",
    image: "/products/ora-ultra-matratze.png",
    priceFrom: 899,
    priceTo: 1699,
    currency: "CHF",
    sizes: ["80×200", "90×200", "100×200", "120×200", "140×200", "160×200", "180×200", "200×200"],
    benefits: [
      "Adaptive Positionierung für jede Schlafposition",
      "Oceans Cool™ Technology gegen Nachtschweiß",
      "Druckentlastung für Rücken und Nacken",
      "Swiss Made — entwickelt und hergestellt in der Schweiz",
    ],
    stats: [
      { value: "93%", label: "berichten von besserem Schlaf und mehr Energie" },
      { value: "60%", label: "schlafen jetzt in unter 10 Minuten ein" },
      { value: "49%", label: "berichten von weniger Rückenschmerzen" },
      { value: "8.6/10", label: "Morgen-Feeling (vorher 5.4)" },
    ],
    badges: ["Testsieger 2026", "Swiss Made", "10 Jahre Garantie", "200 Nächte Probeschlafen"],
    rating: 4.1,
    reviews: 108,
    url: "https://orasleep.ch/products/ora-ultra-matratze",
  },
  {
    slug: "ora-ultra-topper",
    name: "Ora Ultra Topper",
    tagline: "Das Luxus-Upgrade für dein Bett – spürbar weicher, perfekt gestützt.",
    type: "Topper",
    image: "/products/ora-ultra-topper.png",
    priceFrom: 799,
    priceTo: 899,
    currency: "CHF",
    sizes: ["160×200", "180×200", "200×200"],
    benefits: [
      "Druckentlastung für Schultern und Hüfte",
      "Atmungsaktiv für trockenes Schlafklima",
      "Elastischer Grip — rutscht nicht",
      "Swiss Made Qualität",
    ],
    stats: [],
    badges: ["Swiss Made", "200 Nächte Probeschlafen"],
    rating: null,
    reviews: null,
    url: "https://orasleep.ch/products/ora-ultra-topper",
  },
];

export default function ProductsPage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="sticky top-[57px] z-40 bg-surface/95 backdrop-blur-sm border-b border-border px-6 py-2.5">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-sm font-semibold text-foreground">Produkte</h1>
            <p className="text-[11px] text-muted">
              {PRODUCTS.length} Produkte · Freisteller verfügbar
            </p>
          </div>
        </div>
      </div>

      <main className="p-6 space-y-6">
        {PRODUCTS.map((product) => (
          <div
            key={product.slug}
            className="bg-surface border border-border rounded-2xl overflow-hidden"
          >
            <div className="flex flex-col lg:flex-row">
              {/* Image */}
              <div className="lg:w-[340px] shrink-0 bg-gradient-to-br from-background to-surface flex items-center justify-center p-8 lg:p-10 border-b lg:border-b-0 lg:border-r border-border">
                <img
                  src={product.image}
                  alt={product.name}
                  className="max-h-[240px] max-w-full object-contain drop-shadow-lg"
                />
              </div>

              {/* Content */}
              <div className="flex-1 p-6 lg:p-8">
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div>
                    <span className="text-[10px] uppercase tracking-wider font-semibold text-accent">
                      {product.type}
                    </span>
                    <h2 className="text-xl font-bold text-foreground mt-0.5">
                      {product.name}
                    </h2>
                    <p className="text-sm text-muted mt-1 max-w-lg">
                      {product.tagline}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <div className="text-lg font-bold text-foreground">
                      ab {product.currency} {product.priceFrom}
                    </div>
                    {product.priceTo !== product.priceFrom && (
                      <div className="text-[11px] text-muted">
                        bis {product.currency} {product.priceTo}
                      </div>
                    )}
                    {product.rating && (
                      <div className="text-[11px] text-muted mt-1">
                        ★ {product.rating} · {product.reviews} Reviews
                      </div>
                    )}
                  </div>
                </div>

                {/* Badges */}
                <div className="flex flex-wrap gap-1.5 mt-4">
                  {product.badges.map((badge) => (
                    <span
                      key={badge}
                      className="text-[10px] font-semibold bg-primary/10 text-primary px-2 py-1 rounded-md"
                    >
                      {badge}
                    </span>
                  ))}
                </div>

                {/* Benefits */}
                <div className="mt-5">
                  <div className="text-[10px] uppercase tracking-wider font-semibold text-muted mb-2">
                    Key Benefits
                  </div>
                  <ul className="space-y-1.5">
                    {product.benefits.map((b, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-foreground">
                        <span className="text-accent mt-0.5 shrink-0">✓</span>
                        {b}
                      </li>
                    ))}
                  </ul>
                </div>

                {/* Stats */}
                {product.stats.length > 0 && (
                  <div className="mt-5">
                    <div className="text-[10px] uppercase tracking-wider font-semibold text-muted mb-2">
                      Kundendaten (aus Umfrage, 108 Antworten)
                    </div>
                    <div className="grid grid-cols-2 xl:grid-cols-4 gap-3">
                      {product.stats.map((s, i) => (
                        <div
                          key={i}
                          className="bg-background rounded-lg px-3 py-2.5"
                        >
                          <div className="text-lg font-bold text-primary">
                            {s.value}
                          </div>
                          <div className="text-[11px] text-muted leading-snug mt-0.5">
                            {s.label}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Sizes */}
                <div className="mt-5">
                  <div className="text-[10px] uppercase tracking-wider font-semibold text-muted mb-2">
                    Verfügbare Größen
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {product.sizes.map((s) => (
                      <span
                        key={s}
                        className="text-[11px] font-mono bg-background text-muted border border-border px-2 py-1 rounded-md"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Link */}
                <div className="mt-5 pt-4 border-t border-border">
                  <a
                    href={product.url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-[11px] text-primary hover:text-primary/80 underline transition-colors"
                  >
                    Auf orasleep.ch ansehen →
                  </a>
                </div>
              </div>
            </div>
          </div>
        ))}
      </main>
    </div>
  );
}
