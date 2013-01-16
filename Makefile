
test:
	python `which nosetests` --with-pylons=test-core.ini ckanext/canada/tests 2>&1
