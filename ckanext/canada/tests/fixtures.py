import pytest
from ckan.tests.helpers import reset_db
from ckanapi import LocalCKAN
from factory import Sequence
from ckanext.canada.tests.factories import CanadaOrganization as Organization

import logging
log = logging.getLogger(__name__)


@pytest.fixture
def prepare_dataset_type_with_resources(request):
    reset_db()
    dataset_type = request.param.get('dataset_type', None)
    resource_key = request.param.get('resource_key', 0)
    cache_variables = request.param.get('cache_variables', ['resource_id'])

    org = Organization()
    lc = LocalCKAN()

    log.info('Creating organization with id: {}'.format(org['name']))
    log.info('Setting organization dataset type to {}'.format(dataset_type))

    lc.action.recombinant_create(dataset_type=dataset_type, owner_org=org['name'])
    rval = lc.action.recombinant_show(dataset_type=dataset_type, owner_org=org['name'])

    for variable in cache_variables:
        if variable == 'resource_id':
            cache_value = rval['resources'][resource_key]['id']
        elif variable == 'pkg_id':
            cache_value = rval['id']
        elif variable == 'org':
            cache_value = org

        log.info('Setting fixture cache {} variable to: {}'.format(variable, cache_value))

        request.config.cache.set(variable, cache_value)


@pytest.fixture
def prepare_org_editor_member(request):
    reset_db()
    sysadmin_user = request.param.get('sysadmin_user', Sequence(lambda n: "test_sysadmin_{0:02d}".format(n)))
    normal_user = request.param.get('normal_user', Sequence(lambda n: "test_user_{0:02d}".format(n)))
    org_name = request.param.get('org_name', Sequence(lambda n: "test_org_{0:02d}".format(n)))

    sysadmin_action = LocalCKAN(
        username=sysadmin_user).action

    sysadmin_action.organization_member_create(
        username=normal_user,
        id=org_name,
        role='editor')

    log.info('Creating member with username: {}'.format(normal_user))
    log.info('Adding member as an editor to orginaztion: {}'.format(org_name))
