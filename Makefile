
test:
	python `which nosetests` --with-pylons=test-core.ini ckanext/canada/tests 2>&1

tune-database-clear-solr:
	paster --plugin=ckan db init
	paster --plugin=ckan search-index clear
	bash -c "`tuning/psql_args.py development.ini`" < tuning/constraints.sql
	bash -c "`tuning/psql_args.py development.ini`" < tuning/what_to_alter.sql
	paster canada create-vocabularies
	paster canada create-organizations
	paster --plugin=ckan sysadmin add admin

production-database-init:
	# apply postgis tables from redhat-specific paths
	bash -c "`tuning/psql_args.py development.ini`" < /usr/share/pgsql/contrib/postgis-64.sql
	bash -c "`tuning/psql_args.py development.ini`" < /usr/share/pgsql/contrib/postgis-1.5/spatial_ref_sys.sql
	paster --plugin=ckan db init
	paster --plugin=ckan search-index clear
	paster canada create-vocabularies
	paster canada create-organizations

