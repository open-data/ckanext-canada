from setuptools import setup, find_packages
import sys, os

version = '0.3.0'

setup(
    name='ckanext-canada',
    version=version,
    description="Open Canada CKAN extension",
    long_description="""
    """,
    classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    keywords='',
    author='Government of Canada',
    author_email='Michel.Gendron@statcan.gc.ca',
    url='',
    license='MIT',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # -*- Extra requirements: -*-
    ],
    entry_points=\
    """
    [ckan.plugins]
    canada_internal=ckanext.canada.plugins:DataGCCAInternal
    canada_public=ckanext.canada.plugins:DataGCCAPublic
    canada_forms=ckanext.canada.plugins:DataGCCAForms
    canada_package=ckanext.canada.plugins:DataGCCAPackageController

    [paste.paster_command]
    canada=ckanext.canada.commands:CanadaCommand
    ati=ckanext.canada.ati:ATICommand

    contracts=ckanext.canada.pdnil:PDNilCommand
    grants=ckanext.canada.pdnil:PDNilCommand
    reclassification=ckanext.canada.pdnil:PDNilCommand
    travela=ckanext.canada.pd:PDCommand
    travelq=ckanext.canada.pdnil:PDNilCommand
    hospitalityq=ckanext.canada.pdnil:PDNilCommand
    contractsa=ckanext.canada.pd:PDCommand
    inventory=ckanext.canada.pd:PDCommand
    wrongdoing=ckanext.canada.pd:PDCommand
    """,
)
