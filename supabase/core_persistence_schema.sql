CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS public.cs_vendors (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  website TEXT UNIQUE NOT NULL,
  source TEXT,
  mission TEXT,
  usp TEXT,
  pricing TEXT,
  icp_buyer JSONB DEFAULT '[]'::jsonb,
  free_trial BOOLEAN,
  soc2 BOOLEAN,
  founded TEXT,
  products JSONB DEFAULT '[]'::jsonb,
  leadership JSONB DEFAULT '[]'::jsonb,
  company_hq TEXT,
  contact_email TEXT,
  contact_page_url TEXT,
  demo_url TEXT,
  help_center_url TEXT,
  support_url TEXT,
  about_url TEXT,
  team_url TEXT,
  integration_categories TEXT[] DEFAULT '{}'::text[],
  integrations TEXT[] DEFAULT '{}'::text[],
  support_signals TEXT[] DEFAULT '{}'::text[],
  use_cases TEXT[] DEFAULT '{}'::text[],
  lifecycle_stages TEXT[] DEFAULT '{}'::text[],
  case_study_details JSONB DEFAULT '[]'::jsonb,
  raw_description TEXT,
  confidence TEXT,
  first_seen DATE DEFAULT CURRENT_DATE,
  last_updated TIMESTAMPTZ DEFAULT NOW(),
  is_new BOOLEAN DEFAULT TRUE
);

ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS icp TEXT[] DEFAULT '{}'::text[];
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS case_studies TEXT[] DEFAULT '{}'::text[];
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS customers TEXT[] DEFAULT '{}'::text[];
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS value_statements TEXT[] DEFAULT '{}'::text[];
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS evidence_urls TEXT[] DEFAULT '{}'::text[];
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS directory_fit TEXT;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS directory_category TEXT;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS include_in_directory BOOLEAN DEFAULT FALSE;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS raw_description TEXT;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS mission TEXT;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS usp TEXT;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS pricing TEXT;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS icp_buyer JSONB DEFAULT '[]'::jsonb;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS free_trial BOOLEAN;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS soc2 BOOLEAN;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS founded TEXT;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS products JSONB DEFAULT '[]'::jsonb;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS leadership JSONB DEFAULT '[]'::jsonb;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS company_hq TEXT;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS contact_email TEXT;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS contact_page_url TEXT;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS demo_url TEXT;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS help_center_url TEXT;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS support_url TEXT;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS about_url TEXT;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS team_url TEXT;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS integration_categories TEXT[] DEFAULT '{}'::text[];
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS integrations TEXT[] DEFAULT '{}'::text[];
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS support_signals TEXT[] DEFAULT '{}'::text[];
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS use_cases TEXT[] DEFAULT '{}'::text[];
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS lifecycle_stages TEXT[] DEFAULT '{}'::text[];
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS case_study_details JSONB DEFAULT '[]'::jsonb;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS confidence TEXT;
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS last_updated TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE public.cs_vendors ADD COLUMN IF NOT EXISTS is_new BOOLEAN DEFAULT TRUE;

CREATE TABLE IF NOT EXISTS public.discovery_candidates (
  candidate_domain TEXT PRIMARY KEY,
  candidate_title TEXT,
  candidate_description TEXT,
  source_query TEXT,
  source_engine TEXT,
  source_rank INTEGER,
  discovered_at TIMESTAMPTZ NOT NULL,
  candidate_status TEXT NOT NULL,
  drop_reason TEXT,
  updated_at TIMESTAMPTZ NOT NULL
);

ALTER TABLE public.discovery_candidates ADD COLUMN IF NOT EXISTS candidate_title TEXT;
ALTER TABLE public.discovery_candidates ADD COLUMN IF NOT EXISTS candidate_description TEXT;
ALTER TABLE public.discovery_candidates ADD COLUMN IF NOT EXISTS source_query TEXT;
ALTER TABLE public.discovery_candidates ADD COLUMN IF NOT EXISTS source_engine TEXT;
ALTER TABLE public.discovery_candidates ADD COLUMN IF NOT EXISTS source_rank INTEGER;
ALTER TABLE public.discovery_candidates ADD COLUMN IF NOT EXISTS discovered_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE public.discovery_candidates ADD COLUMN IF NOT EXISTS candidate_status TEXT NOT NULL DEFAULT 'new';
ALTER TABLE public.discovery_candidates ADD COLUMN IF NOT EXISTS drop_reason TEXT;
ALTER TABLE public.discovery_candidates ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE TABLE IF NOT EXISTS public.pipeline_runs (
  run_id TEXT PRIMARY KEY,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  queries_executed TEXT,
  candidate_count INTEGER,
  queued_count INTEGER,
  skipped_existing_count INTEGER,
  enriched_count INTEGER,
  dropped_count INTEGER,
  llm_success_count INTEGER,
  llm_fallback_count INTEGER,
  run_status TEXT,
  error_summary TEXT
);

ALTER TABLE public.pipeline_runs ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ;
ALTER TABLE public.pipeline_runs ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
ALTER TABLE public.pipeline_runs ADD COLUMN IF NOT EXISTS queries_executed TEXT;
ALTER TABLE public.pipeline_runs ADD COLUMN IF NOT EXISTS candidate_count INTEGER;
ALTER TABLE public.pipeline_runs ADD COLUMN IF NOT EXISTS queued_count INTEGER;
ALTER TABLE public.pipeline_runs ADD COLUMN IF NOT EXISTS skipped_existing_count INTEGER;
ALTER TABLE public.pipeline_runs ADD COLUMN IF NOT EXISTS enriched_count INTEGER;
ALTER TABLE public.pipeline_runs ADD COLUMN IF NOT EXISTS dropped_count INTEGER;
ALTER TABLE public.pipeline_runs ADD COLUMN IF NOT EXISTS llm_success_count INTEGER;
ALTER TABLE public.pipeline_runs ADD COLUMN IF NOT EXISTS llm_fallback_count INTEGER;
ALTER TABLE public.pipeline_runs ADD COLUMN IF NOT EXISTS run_status TEXT;
ALTER TABLE public.pipeline_runs ADD COLUMN IF NOT EXISTS error_summary TEXT;
