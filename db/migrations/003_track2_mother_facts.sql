ALTER TABLE households ADD COLUMN state TEXT;
ALTER TABLE mothers ADD COLUMN is_pregnant INTEGER NOT NULL DEFAULT 0 CHECK (is_pregnant IN (0, 1));
ALTER TABLE mothers ADD COLUMN is_lactating INTEGER NOT NULL DEFAULT 0 CHECK (is_lactating IN (0, 1));
ALTER TABLE mothers ADD COLUMN trimester INTEGER CHECK (trimester IN (1, 2, 3));
ALTER TABLE mothers ADD COLUMN planned_delivery_facility TEXT CHECK (planned_delivery_facility IN ('government', 'accredited_private'));
