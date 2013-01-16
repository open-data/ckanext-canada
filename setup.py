from setuptools import setup, find_packages
import sys, os

version = '0.1.2'

setup(
	name='ckanext-canada',
	version=version,
	description="data.gc.ca CKAN extension",
	long_description="""\
	""",
	classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
	keywords='',
	author='Government of Canada',
	author_email='Michel.Gendron@statcan.gc.ca',
	url='',
	license='MIT',
	packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
	namespace_packages=['ckanext', 'ckanext.canada'],
	include_package_data=True,
	zip_safe=False,
	install_requires=[
		# -*- Extra requirements: -*-
	],
	entry_points=\
	"""
        [ckan.plugins]
	canada_public=ckanext.canada.plugins:DataGCCAPublic

        [nose.plugins.0.10]
        canada_nose_plugin = ckanext.canada.nose_plugin:DataGCCANosePlugin
	""",
        test_suite="ckanext.canada.tests",
)
