
CKAN_CONFIG ?= development.ini

ifeq ($(wildcard ${CKAN_CONFIG}),)
$(error CKAN configuration file ${CKAN_CONFIG} not found, you may \
        want to specify an override for the CKAN_CONFIG value)
endif

PSQL_COMMAND = $(shell bin/psql_args.py ${CKAN_CONFIG})
DB_NAME_PORT = $(shell bin/psql_dbname.py ${CKAN_CONFIG})
DB_USER = $(shell bin/psql_user.py ${CKAN_CONFIG})
TEST_TEMPLATE = test_template

POSTGIS = $(firstword $(wildcard \
    /usr/share/pgsql/contrib/postgis-64.sql \
    /usr/share/postgresql/*/contrib/postgis-1.5/postgis.sql \
    ))
SPATIAL_REF_SYS = $(firstword $(wildcard \
    /usr/share/pgsql/contrib/postgis-1.5/spatial_ref_sys.sql \
    /usr/share/postgresql/*/contrib/postgis-1.5/spatial_ref_sys.sql \
    ))

test:
	sudo -u postgres dropdb ${DB_NAME_PORT}
	sudo -u postgres createdb ${DB_NAME_PORT} -O ${DB_USER} -T ${TEST_TEMPLATE}
	nosetests --with-pylons=${CKAN_CONFIG} --nologcapture ckanext/canada/tests 2>&1

drop-database:
	-sudo -u postgres dropdb ${DB_NAME_PORT}

create-database:
	sudo -u postgres createdb ${DB_NAME_PORT} -O ${DB_USER} -E UTF-8
	sudo -u postgres psql ${DB_NAME_PORT} < ${POSTGIS}
	sudo -u postgres psql ${DB_NAME_PORT} -c "ALTER TABLE spatial_ref_sys OWNER TO ${DB_USER}"
	sudo -u postgres psql ${DB_NAME_PORT} -c "ALTER TABLE geometry_columns OWNER TO ${DB_USER}"
	bash -c "${PSQL_COMMAND}" < ${SPATIAL_REF_SYS}
	paster --plugin=ckan db init -c ${CKAN_CONFIG}
	paster --plugin=ckan search-index clear -c ${CKAN_CONFIG}
	paster canada create-vocabularies -c ${CKAN_CONFIG}
	paster canada create-organizations -c ${CKAN_CONFIG}
	paster --plugin=ckan sysadmin add admin -c ${CKAN_CONFIG}

tune-database:
	bash -c "${PSQL_COMMAND}" < tuning/constraints.sql
	bash -c "${PSQL_COMMAND}" < tuning/what_to_alter.sql

create-test-template: drop-database create-database
	-sudo -u postgres dropdb ${TEST_TEMPLATE} \
            $(wordlist 2, 3, ${DB_NAME_PORT})
	sudo -u postgres createdb ${TEST_TEMPLATE} -T ${DB_NAME_PORT}

