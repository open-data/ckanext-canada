# -*- coding: utf-8 -*-
from setuptools import setup, find_packages
version = '0.4.0'

setup(
    name='ckanext-canada',
    version=version,
    description="Open Canada CKAN extension",
    long_description="""
    """,
    classifiers=[],
    keywords='',
    author='Government of Canada',
    author_email='Ross.Thompson@tbs-sct.gc.ca',
    url='',
    license='MIT',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['ckanext'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        # -*- Extra requirements: -*-
    ],
    entry_points="""
    [ckan.plugins]
    canada_internal=ckanext.canada.plugins:DataGCCAInternal
    canada_public=ckanext.canada.plugins:DataGCCAPublic
    canada_forms=ckanext.canada.plugins:DataGCCAForms
    canada_datasets=ckanext.canada.plugins:CanadaDatasetsPlugin
    canada_security=ckanext.canada.plugins:CanadaSecurityPlugin

    [paste.paster_command]
    canada=ckanext.canada.commands:CanadaCommand

    ati=ckanext.canada.pd:PDNilCommand
    contracts=ckanext.canada.pd:PDNilCommand
    grants=ckanext.canada.pd:PDNilCommand
    reclassification=ckanext.canada.pd:PDNilCommand
    travela=ckanext.canada.pd:PDCommand
    travelq=ckanext.canada.pd:PDNilCommand
    hospitalityq=ckanext.canada.pd:PDNilCommand
    contractsa=ckanext.canada.pd:PDCommand
    inventory=ckanext.canada.pd:PDCommand
    wrongdoing=ckanext.canada.pd:PDCommand

    [babel.extractors]
    ckan = ckan.lib.extract:extract_ckan
    """,
    message_extractors={
        'ckanext': [
            ('**.py', 'python', None),
            ('**.js', 'javascript', None),
            ('**/templates/**.html', 'ckan', None),
        ],
    }
)
