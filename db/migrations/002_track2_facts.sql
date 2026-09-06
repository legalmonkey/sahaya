-- Track 2 eligibility facts. These are explicit evidence fields, not inferred
-- proxies such as a guessed income band.
ALTER TABLE households ADD COLUMN annual_income_inr INTEGER;
ALTER TABLE households ADD COLUMN has_bpl_ration_card INTEGER NOT NULL DEFAULT 0 CHECK (has_bpl_ration_card IN (0, 1));
ALTER TABLE households ADD COLUMN has_nfsa_ration_card INTEGER NOT NULL DEFAULT 0 CHECK (has_nfsa_ration_card IN (0, 1));
ALTER TABLE households ADD COLUMN has_e_shram_card INTEGER NOT NULL DEFAULT 0 CHECK (has_e_shram_card IN (0, 1));
ALTER TABLE households ADD COLUMN has_mgnrega_job_card INTEGER NOT NULL DEFAULT 0 CHECK (has_mgnrega_job_card IN (0, 1));
ALTER TABLE households ADD COLUMN is_pm_kisan_beneficiary INTEGER NOT NULL DEFAULT 0 CHECK (is_pm_kisan_beneficiary IN (0, 1));
ALTER TABLE households ADD COLUMN is_pmjay_listed INTEGER NOT NULL DEFAULT 0 CHECK (is_pmjay_listed IN (0, 1));
ALTER TABLE households ADD COLUMN is_disabled_40_percent INTEGER NOT NULL DEFAULT 0 CHECK (is_disabled_40_percent IN (0, 1));
ALTER TABLE households ADD COLUMN has_pmmvy_eligible_worker INTEGER NOT NULL DEFAULT 0 CHECK (has_pmmvy_eligible_worker IN (0, 1));
