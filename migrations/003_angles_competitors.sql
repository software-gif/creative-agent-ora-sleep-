-- Migration 003: Angles + Competitors for Board display
-- Run in the Supabase SQL Editor for project cwwxtuuacxulrhvrilmu
--
-- Adds four tables so the Board can render /angles and /competitors pages
-- and so skills (competitor-ad-analysis, briefing-agent, static-ads) can
-- read a single source of truth instead of local JSON files.

-- ---------------------------------------------------------------------------
-- Angles
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS angles (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  brand_id        UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  key             TEXT NOT NULL,
  name            TEXT NOT NULL,
  type            TEXT NOT NULL,
  data_point      TEXT,
  priority        INTEGER DEFAULT 0,
  status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
  last_updated_at TIMESTAMPTZ DEFAULT now(),
  created_at      TIMESTAMPTZ DEFAULT now(),
  UNIQUE (brand_id, key)
);

-- Child table: headline and hook variants per angle (Option B)
-- Lets Sandro disable individual variants if they don't perform.
CREATE TABLE IF NOT EXISTS angle_variants (
  id            UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  angle_id      UUID NOT NULL REFERENCES angles(id) ON DELETE CASCADE,
  variant_type  TEXT NOT NULL CHECK (variant_type IN ('headline', 'hook')),
  content       TEXT NOT NULL,
  display_order INTEGER DEFAULT 0,
  status        TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
  created_at    TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_angles_brand_key     ON angles (brand_id, key);
CREATE INDEX IF NOT EXISTS idx_angle_variants_angle ON angle_variants (angle_id);

-- ---------------------------------------------------------------------------
-- Competitors
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS competitors (
  id                UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  brand_id          UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  name              TEXT NOT NULL,
  slug              TEXT NOT NULL,
  market            TEXT,
  website           TEXT,
  facebook_page_id  TEXT,
  trustpilot_url    TEXT,
  status            TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'watching', 'excluded')),
  notes             TEXT,
  last_analyzed_at  TIMESTAMPTZ,
  created_at        TIMESTAMPTZ DEFAULT now(),
  UNIQUE (brand_id, slug)
);

-- Snapshot of each analysis run — keeps history so we can compare over time.
CREATE TABLE IF NOT EXISTS competitor_analyses (
  id             UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  competitor_id  UUID NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,
  batch_id       UUID,
  summary_json   JSONB,
  report_md      TEXT,
  ads_count      INTEGER DEFAULT 0,
  top_winners    JSONB,
  created_at     TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_competitors_brand              ON competitors (brand_id);
CREATE INDEX IF NOT EXISTS idx_competitor_analyses_competitor ON competitor_analyses (competitor_id);

-- ---------------------------------------------------------------------------
-- RLS (match migration 001 permissive pattern — anon client needs read)
-- ---------------------------------------------------------------------------

ALTER TABLE angles              ENABLE ROW LEVEL SECURITY;
ALTER TABLE angle_variants      ENABLE ROW LEVEL SECURITY;
ALTER TABLE competitors         ENABLE ROW LEVEL SECURITY;
ALTER TABLE competitor_analyses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read angles"       ON angles       FOR SELECT USING (true);
CREATE POLICY "Public insert angles"     ON angles       FOR INSERT WITH CHECK (true);
CREATE POLICY "Public update angles"     ON angles       FOR UPDATE USING (true);
CREATE POLICY "Public delete angles"     ON angles       FOR DELETE USING (true);

CREATE POLICY "Public read angle_variants"   ON angle_variants FOR SELECT USING (true);
CREATE POLICY "Public insert angle_variants" ON angle_variants FOR INSERT WITH CHECK (true);
CREATE POLICY "Public update angle_variants" ON angle_variants FOR UPDATE USING (true);
CREATE POLICY "Public delete angle_variants" ON angle_variants FOR DELETE USING (true);

CREATE POLICY "Public read competitors"   ON competitors FOR SELECT USING (true);
CREATE POLICY "Public insert competitors" ON competitors FOR INSERT WITH CHECK (true);
CREATE POLICY "Public update competitors" ON competitors FOR UPDATE USING (true);
CREATE POLICY "Public delete competitors" ON competitors FOR DELETE USING (true);

CREATE POLICY "Public read competitor_analyses"   ON competitor_analyses FOR SELECT USING (true);
CREATE POLICY "Public insert competitor_analyses" ON competitor_analyses FOR INSERT WITH CHECK (true);
CREATE POLICY "Public delete competitor_analyses" ON competitor_analyses FOR DELETE USING (true);
