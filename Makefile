
test:
	python `which nosetests` --ckan --with-pylons=test-core.ini ckanext/canada/tests 2>&1
