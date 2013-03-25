
test:
	python `which nosetests` --with-pylons=test-core.ini ckanext/canada/tests 2>&1

tune-database-clear-solr:
	paster --plugin=ckan db init
	paster --plugin=ckan search-index clear
	bash -c "`tuning/psql_args.py development.ini`" < tuning/constraints.sql
	bash -c "`tuning/psql_args.py development.ini`" < tuning/what_to_alter.sql
	paster canada create-vocabularies
	paster --plugin=ckan sysadmin add admin
