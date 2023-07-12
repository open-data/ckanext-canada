from ckanext.validation.model import create_tables, tables_exist

def canada_tests_init_validation():
 if not tables_exist():
  create_tables()
