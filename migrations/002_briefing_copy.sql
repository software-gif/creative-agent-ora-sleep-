-- Migration: Briefing + Meta Copy fields for creatives
-- Run in the Supabase SQL Editor for project cwwxtuuacxulrhvrilmu

-- Meta-optimized ad copy
ALTER TABLE creatives ADD COLUMN IF NOT EXISTS primary_text TEXT;
ALTER TABLE creatives ADD COLUMN IF NOT EXISTS headlines TEXT[];
ALTER TABLE creatives ADD COLUMN IF NOT EXISTS description TEXT;
ALTER TABLE creatives ADD COLUMN IF NOT EXISTS cta TEXT;

-- Briefing context (why this creative, target audience, angle rationale)
ALTER TABLE creatives ADD COLUMN IF NOT EXISTS briefing_rationale TEXT;
ALTER TABLE creatives ADD COLUMN IF NOT EXISTS target_audience TEXT;

-- Timestamp so we know when copy was last generated
ALTER TABLE creatives ADD COLUMN IF NOT EXISTS copy_generated_at TIMESTAMPTZ;
