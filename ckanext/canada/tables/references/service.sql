-- Program IDs
DROP TABLE IF EXISTS ref_service_program_ids;
CREATE TABLE ref_service_program_ids (
  _id SMALLSERIAL,  -- needed for datastore_search
  program_id TEXT PRIMARY KEY,
  label_en TEXT NOT NULL,
  label_fr TEXT NOT NULL,
  org_years JSONB
);

DROP INDEX IF EXISTS idx_ref_service_program_ids_org_years;
CREATE INDEX idx_ref_service_program_ids_org_years ON ref_service_program_ids USING GIN (org_years);

GRANT SELECT ON TABLE ref_service_program_ids TO {readuser};
ALTER TABLE ref_service_program_ids OWNER TO {writeuser};

-- Service IDs
DROP TABLE IF EXISTS ref_service_service_ids;
CREATE TABLE ref_service_service_ids (
  _id SMALLSERIAL,  -- needed for datastore_search
  service_id TEXT PRIMARY KEY,
  label_en TEXT NOT NULL,
  label_fr TEXT NOT NULL,
  org_years JSONB
);

DROP INDEX IF EXISTS idx_ref_service_service_ids_org_years;
CREATE INDEX idx_ref_service_service_ids_org_years ON ref_service_service_ids USING GIN (org_years);

GRANT SELECT ON TABLE ref_service_service_ids TO {readuser};
ALTER TABLE ref_service_service_ids OWNER TO {writeuser};
