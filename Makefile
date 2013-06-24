
CKAN_CONFIG ?= development.ini
DB_TEMPLATE ?= test_template

ifeq ($(wildcard ${CKAN_CONFIG}),)
$(error CKAN configuration file ${CKAN_CONFIG} not found, you may \
        want to specify an override for the CKAN_CONFIG value)
endif

PSQL_COMMAND = $(shell bin/psql_args.py ${CKAN_CONFIG})
DB_NAME_PORT = $(shell bin/psql_dbname.py ${CKAN_CONFIG})
DB_USER = $(shell bin/psql_user.py ${CKAN_CONFIG})

test: reset-database
	nosetests --with-pylons=${CKAN_CONFIG} --nologcapture ckanext/canada/tests 2>&1

drop-database:
	-sudo -u postgres dropdb ${DB_NAME_PORT}

build-database: drop-database
	sudo -u postgres createdb ${DB_NAME_PORT} -O ${DB_USER} -E UTF-8
	paster --plugin=ckan db init -c ${CKAN_CONFIG}
	paster --plugin=ckan search-index clear -c ${CKAN_CONFIG}
	paster canada create-vocabularies -c ${CKAN_CONFIG}
	paster canada create-organizations -c ${CKAN_CONFIG}
	paster --plugin=ckan sysadmin add admin -c ${CKAN_CONFIG}

tune-database:
	bash -c "${PSQL_COMMAND}" < tuning/constraints.sql
	bash -c "${PSQL_COMMAND}" < tuning/what_to_alter.sql

build-database-template: drop-database build-database
	-sudo -u postgres dropdb ${DB_TEMPLATE} \
            $(wordlist 2, 3, ${DB_NAME_PORT})
	sudo -u postgres createdb ${DB_TEMPLATE} -T ${DB_NAME_PORT}

reset-database: drop-database
	sudo -u postgres createdb ${DB_NAME_PORT} -T ${DB_TEMPLATE}
