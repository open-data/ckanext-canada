
test:
	python /usr/lib/ckan/bin/nosetests --ckan --with-pylons=test-core.ini ckanext/canada/tests 2>&1
