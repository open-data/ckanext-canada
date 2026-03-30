-- Program IDs
DROP TABLE IF EXISTS ref_service_program_ids;
DROP TYPE IF EXISTS SERVICE_ORG_YEAR;
CREATE TYPE SERVICE_ORG_YEAR AS (org_id TEXT, fiscal_year TEXT);
CREATE TABLE ref_service_program_ids (
  _id SMALLSERIAL,  -- needed for datastore_search
  program_id TEXT PRIMARY KEY,
  label_en TEXT NOT NULL,
  label_fr TEXT NOT NULL,
  service_ids TEXT[],
  org_years SERVICE_ORG_YEAR[]
);

GRANT SELECT ON TABLE ref_service_program_ids TO {readuser};
ALTER TABLE ref_service_program_ids OWNER TO {writeuser};

-- Service IDs
DROP TABLE IF EXISTS ref_service_service_ids;
CREATE TABLE ref_service_service_ids (
  _id SMALLSERIAL,  -- needed for datastore_search
  service_id TEXT PRIMARY KEY,
  label_en TEXT NOT NULL,
  label_fr TEXT NOT NULL,
  org TEXT NOT NULL
);

GRANT SELECT ON TABLE ref_service_service_ids TO {readuser};
ALTER TABLE ref_service_service_ids OWNER TO {writeuser};
