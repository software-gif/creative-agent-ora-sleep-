-- Migration 004: Meta Upload Prep
-- Adds the fields and support tables needed to finish approved creatives
-- for Meta Ads Manager upload (naming, campaign, ad set, destination url).

-- ---------------------------------------------------------------------------
-- New columns on creatives
-- ---------------------------------------------------------------------------

ALTER TABLE creatives ADD COLUMN IF NOT EXISTS meta_ad_name         TEXT;
ALTER TABLE creatives ADD COLUMN IF NOT EXISTS meta_campaign        TEXT;
ALTER TABLE creatives ADD COLUMN IF NOT EXISTS meta_ad_set          TEXT;
ALTER TABLE creatives ADD COLUMN IF NOT EXISTS meta_destination_url TEXT;
ALTER TABLE creatives ADD COLUMN IF NOT EXISTS meta_ready           BOOLEAN DEFAULT FALSE;
ALTER TABLE creatives ADD COLUMN IF NOT EXISTS approved_at          TIMESTAMPTZ;

-- ---------------------------------------------------------------------------
-- User-defined variables ({{key}} → value) for naming templates + bulk apply
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS meta_variables (
  id         UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  brand_id   UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  key        TEXT NOT NULL,
  value      TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (brand_id, key)
);

CREATE INDEX IF NOT EXISTS idx_meta_variables_brand ON meta_variables (brand_id);

-- ---------------------------------------------------------------------------
-- Naming templates — Sandro can create multiple and switch between them
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS meta_templates (
  id              UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  brand_id        UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
  name            TEXT NOT NULL,
  template_string TEXT NOT NULL,
  is_default      BOOLEAN DEFAULT FALSE,
  created_at      TIMESTAMPTZ DEFAULT now(),
  UNIQUE (brand_id, name)
);

CREATE INDEX IF NOT EXISTS idx_meta_templates_brand ON meta_templates (brand_id);

-- ---------------------------------------------------------------------------
-- Auto-timestamp approved_at when a creative becomes approved.
-- Fires BEFORE UPDATE so we can still read OLD for comparison.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION set_approved_at()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.approval_status = 'approved'
     AND (OLD.approval_status IS NULL OR OLD.approval_status <> 'approved') THEN
    NEW.approved_at = now();
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS creatives_set_approved_at ON creatives;
CREATE TRIGGER creatives_set_approved_at
  BEFORE UPDATE ON creatives
  FOR EACH ROW
  EXECUTE FUNCTION set_approved_at();

-- Backfill: any existing approved/live creatives without approved_at get created_at as fallback
UPDATE creatives
SET approved_at = created_at
WHERE approval_status IN ('approved', 'live')
  AND approved_at IS NULL;

-- ---------------------------------------------------------------------------
-- RLS (match migration 001 permissive pattern)
-- ---------------------------------------------------------------------------

ALTER TABLE meta_variables ENABLE ROW LEVEL SECURITY;
ALTER TABLE meta_templates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read meta_variables"   ON meta_variables FOR SELECT USING (true);
CREATE POLICY "Public insert meta_variables" ON meta_variables FOR INSERT WITH CHECK (true);
CREATE POLICY "Public update meta_variables" ON meta_variables FOR UPDATE USING (true);
CREATE POLICY "Public delete meta_variables" ON meta_variables FOR DELETE USING (true);

CREATE POLICY "Public read meta_templates"   ON meta_templates FOR SELECT USING (true);
CREATE POLICY "Public insert meta_templates" ON meta_templates FOR INSERT WITH CHECK (true);
CREATE POLICY "Public update meta_templates" ON meta_templates FOR UPDATE USING (true);
CREATE POLICY "Public delete meta_templates" ON meta_templates FOR DELETE USING (true);

-- ---------------------------------------------------------------------------
-- Seed sensible Ora defaults
-- ---------------------------------------------------------------------------

INSERT INTO meta_variables (brand_id, key, value)
VALUES
  ('2a2349da-09c2-4e00-b739-0c652b7f62ea', 'brand',      'ora'),
  ('2a2349da-09c2-4e00-b739-0c652b7f62ea', 'campaign',   'Evergreen Matratze'),
  ('2a2349da-09c2-4e00-b739-0c652b7f62ea', 'ad_set',     'DACH Women 30-55'),
  ('2a2349da-09c2-4e00-b739-0c652b7f62ea', 'landing',    'https://orasleep.ch/products/ora-ultra-matratze'),
  ('2a2349da-09c2-4e00-b739-0c652b7f62ea', 'utm_source', 'meta_ads')
ON CONFLICT (brand_id, key) DO NOTHING;

INSERT INTO meta_templates (brand_id, name, template_string, is_default)
VALUES
  ('2a2349da-09c2-4e00-b739-0c652b7f62ea',
   'Standard Naming',
   'ora_{{angle}}_{{format}}_{{date}}_v{{variant}}',
   true)
ON CONFLICT (brand_id, name) DO NOTHING;
