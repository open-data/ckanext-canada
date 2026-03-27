-- Program IDs
DROP TABLE IF EXISTS ref_service_program_ids;
CREATE TABLE ref_service_program_ids (
  program_id INT PRIMARY KEY,
  label_en TEXT,
  label_fr TEXT,
  service_ids INT[],
  org_years JSONB
);

GRANT SELECT ON TABLE ref_service_program_ids TO {readuser};
ALTER TABLE ref_service_program_ids OWNER TO {writeuser};

-- Service IDs
DROP TABLE IF EXISTS ref_service_service_ids;
CREATE TABLE ref_service_service_ids (
  service_id TEXT PRIMARY KEY,
  label_en TEXT,
  label_fr TEXT
);

GRANT SELECT ON TABLE ref_service_service_ids TO {readuser};
ALTER TABLE ref_service_service_ids OWNER TO {writeuser};
