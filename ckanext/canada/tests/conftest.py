import os
from pytest import Session
from ckan.tests.helpers import reset_db
from ckan.lib.search import clear_all
from ckanext.validation.model import (
    create_tables as validation_create_tables,
    tables_exist as validation_tables_exist
)
from ckan import model
from ckanext.security.model import db_setup as security_db_setup
from ckanext.canada.tests.factories import CanadaOrganization as Organization
from ckanext.canada.triggers import update_triggers
from ckanext.recombinant.cli import _create_triggers
from ckanext.canada.pd import _load_csv_ref_data
from ckan.cli.db import _run_migrations
from ckanapi import LocalCKAN, NotFound


def pytest_collection_finish(session: Session) -> None:
    print("--- Performing global setup before all tests ---")

    print('Running Canada plugin migrations...')
    try:
        _run_migrations('canada_public')
    except Exception:
        pass

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

    # commit initial migrations
    model.Session.commit()

    print('Running Canada plugin migrations...')
    try:
        _run_migrations('canada_public')
    except Exception:
        pass

    # create test reference data
    print('Loading test reference data...')
    service_id_data = os.path.join(
        os.path.split(__file__)[0],
        'samples/ref_data/test_ref_service_service_ids.csv')
    loaded = _load_csv_ref_data('ref_service_service_ids',
                                [
                                    'service_id',
                                    'label_en',
                                    'label_fr',
                                    'org_years',
                                ],
                                service_id_data, verbose=False)
    if loaded:
        print('Loaded test_ref_service_service_ids.csv into ref_service_service_ids')

    program_id_data = os.path.join(
        os.path.split(__file__)[0],
        'samples/ref_data/test_ref_service_program_ids.csv')
    loaded = _load_csv_ref_data('ref_service_program_ids',
                                [
                                    'program_id',
                                    'label_en',
                                    'label_fr',
                                    'org_years',
                                ],
                                program_id_data, verbose=False)
    if loaded:
        print('Loaded test_ref_service_program_ids.csv into ref_service_program_ids')

    # NOTE: always make a tbs-sct org
    try:
        lc = LocalCKAN()
        lc.action.organization_show(id='tbs-sct')
    except NotFound:
        print('Creating tbs-sct Organization...')
        Organization(id='tbs-sct', name='tbs-sct')

    print('--- Setup complete ---')
