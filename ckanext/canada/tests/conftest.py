from pytest import Session
from ckan.tests.helpers import reset_db
from ckan.lib.search import clear_all
from ckanext.validation.model import (
    create_tables as validation_create_tables,
    tables_exist as validation_tables_exist
)
from ckanext.security.model import db_setup as security_db_setup
from ckanext.canada.tests.factories import CanadaOrganization as Organization
from ckanext.canada.triggers import update_triggers
from ckanext.recombinant.cli import _create_triggers
from ckan.cli.db import _run_migrations
from ckanapi import LocalCKAN, NotFound


def pytest_collection_finish(session: Session) -> None:
    print("--- Performing global setup before all tests ---")

    print('Running Canada plugin migrations...')
    _run_migrations('canada_public')

    print('Refreshing database...')
    reset_db()
    clear_all()

    if not validation_tables_exist():
        print('Creating ckanext-validation tables...')
        validation_create_tables()

    print('Creating ckanext-security tables...')
    security_db_setup()

    print('Running Activity plugin migrations...')
    _run_migrations('activity')

    print('Updating Canada database triggers...')
    update_triggers()

    print('Updating Recombinant database triggers...')
    _create_triggers(dataset_types=[], all_types=True)

    print('Running Canada plugin migrations...')
    _run_migrations('canada_public')

    # NOTE: always make a tbs-sct org
    try:
        lc = LocalCKAN()
        lc.action.organization_show(id='tbs-sct')
    except NotFound:
        print('Creating tbs-sct Organization...')
        Organization(id='tbs-sct', name='tbs-sct')

    print('--- Setup complete ---')
