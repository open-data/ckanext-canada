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
    canada_internal=ckanext.canada.plugin:CanadaInternalPlugin
    canada_public=ckanext.canada.plugin:CanadaPublicPlugin
    canada_forms=ckanext.canada.plugin:CanadaFormsPlugin
    canada_datasets=ckanext.canada.plugin:CanadaDatasetsPlugin
    canada_security=ckanext.canada.plugin:CanadaSecurityPlugin
    canada_theme=ckanext.canada.plugin:CanadaThemePlugin

    [babel.extractors]
    ckan = ckan.lib.extract:extract_ckan
    pd = ckanext.canada.extract:extract_pd
    """,
    message_extractors={
        'ckanext': [
            ('**/tables/**.yaml', 'pd', None),
            ('**.py', 'python', None),
            ('**.js', 'javascript', None),
            ('**/templates/**.html', 'ckan', None),
        ],
    }
)
