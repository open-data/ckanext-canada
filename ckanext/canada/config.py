from flask import has_request_context
from frictionless import system

from typing import Any, Union, Optional
from ckan.types import Context, DataDict
from ckan.common import CKANConfig

from ckan.plugins.toolkit import (
    h,
    request,
    ValidationError
)
from ckan.config.middleware.flask_app import csrf
import ckan.lib.helpers as core_helpers
import ckan.lib.formatters as formatters
from ckanext.activity.model import activity as activity_model
from ckanext.activity.logic.validators import object_id_validators
from ckanext.datastore.backend import postgres as db
from ckanext.datatablesview.blueprint import datatablesview

from ckanext.canada import dataset
from ckanext.canada.logic import datastore_create_temp_user_table
from ckanext.canada.plugin.validation_plugin import CanadaValidationPlugin


def update_config(config: 'CKANConfig'):
    """
    Add template directories and set initial configuration values.

    Assert certain config options that need to be present for the Canada stack.

    Monkey-patch some things.
    """
    config.update({
        "ckan.user_list_limit": 250
    })

    # CKAN 2.10 plugin loading does not allow us to set the schema
    # files in update_config in a way that the load order will work fully.
    scheming_presets = config.get('scheming.presets', '')
    assert 'ckanext.scheming:presets.json' in scheming_presets
    assert 'ckanext.fluent:presets.json' in scheming_presets
    assert 'ckanext.canada:schemas/presets.yaml' in scheming_presets
    assert 'ckanext.validation:presets.json' in scheming_presets

    # Include private datasets in Feeds
    # NOTE: before_dataset_search in dataset_plugin.py will handle permissions
    config['ckan.feeds.include_private'] = True

    # Disable auth settings
    config['ckan.auth.anon_create_dataset'] = False
    config['ckan.auth.create_unowned_dataset'] = False
    config['ckan.auth.create_dataset_if_not_in_organization'] = False
    config['ckan.auth.user_create_groups'] = False
    config['ckan.auth.user_create_organizations'] = False
    config['ckan.auth.create_user_via_api'] = config.get(
        'ckan.auth.create_user_via_api', False)  # allow setting in INI file
    # Enable auth settings
    config['ckan.auth.user_delete_groups'] = True
    config['ckan.auth.user_delete_organizations'] = True
    # NOTE: user register page for Registry is controlled by"
    #           - IP Intranet list
    #           - NGINX redirects
    config['ckan.auth.create_user_via_web'] = True
    # Set auth settings
    config['ckan.auth.roles_that_cascade_to_sub_groups'] = ['admin']

    activity_model.activity_dictize = dataset.activity_dictize

    csrf.exempt(datatablesview)

    config['ckan.auth.public_user_details'] = False
    config['ckan.auth.public_activity_stream_detail'] = False

    recombinant_definitions = config.get('recombinant.definitions', '')
    assert 'ckanext.canada:tables/ati.yaml' in recombinant_definitions
    assert 'ckanext.canada:tables/briefingt.yaml' in recombinant_definitions
    assert 'ckanext.canada:tables/qpnotes.yaml' in recombinant_definitions
    assert 'ckanext.canada:tables/contracts.yaml' in recombinant_definitions
    assert 'ckanext.canada:tables/contractsa.yaml' in recombinant_definitions
    assert 'ckanext.canada:tables/grants.yaml' in recombinant_definitions
    assert 'ckanext.canada:tables/hospitalityq.yaml' in recombinant_definitions
    assert 'ckanext.canada:tables/reclassification.yaml' in recombinant_definitions
    assert 'ckanext.canada:tables/travela.yaml' in recombinant_definitions
    assert 'ckanext.canada:tables/travelq.yaml' in recombinant_definitions
    assert 'ckanext.canada:tables/wrongdoing.yaml' in recombinant_definitions
    assert 'ckanext.canada:tables/inventory.yaml' in recombinant_definitions
    assert 'ckanext.canada:tables/consultations.yaml' in recombinant_definitions
    assert 'ckanext.canada:tables/service.yaml' in recombinant_definitions
    assert 'ckanext.canada:tables/dac.yaml' in recombinant_definitions
    assert 'ckanext.canada:tables/nap5.yaml' in recombinant_definitions
    assert 'ckanext.canada:tables/experiment.yaml' in recombinant_definitions
    assert 'ckanext.canada:tables/adminaircraft.yaml' in recombinant_definitions
    assert 'ckanext.canada:tables/aistrategy.yaml' in recombinant_definitions

    config['ckan.search.show_all_types'] = True
    config['ckan.gravatar_default'] = 'disabled'
    config['search.facets.limit'] = 200  # because org list

    scheming_presets = config.get('scheming.presets', '')
    if 'validation' not in scheming_presets:
        assert 'ckanext.scheming:presets.json' in scheming_presets
        assert 'ckanext.fluent:presets.json' in scheming_presets
        assert 'ckanext.canada:schemas/presets.yaml' in scheming_presets
        assert 'ckanext.canada:schemas/validation_placeholder_presets.yaml' in \
            scheming_presets

    scheming_dataset_schemas = config.get('scheming.dataset_schemas', '')
    assert 'ckanext.canada:schemas/dataset.yaml' in scheming_dataset_schemas
    assert 'ckanext.canada:schemas/info.yaml' in scheming_dataset_schemas
    assert 'ckanext.canada:schemas/prop.yaml' in scheming_dataset_schemas

    scheming_organization_schemas = config.get('scheming.organization_schemas', '')
    assert 'ckanext.canada:schemas/organization.yaml' in \
        scheming_organization_schemas

    # Pretty output for Feeds
    config['ckan.feeds.pretty'] = True

    # Enable our custom DCAT profile.
    config['ckanext.dcat.rdf.profiles'] = 'euro_dcat_ap_2'

    # Enable license restriction
    config['ckan.dataset.restrict_license_choices'] = True

    # monkey patch helpers.py pagination method
    core_helpers.Page.pager = _wet_pager
    core_helpers.SI_number_span = _SI_number_span_close

    core_helpers.build_nav_main = build_nav_main

    # migration from `canada_activity` and `ckanext-extendedactivity` - Aug 2022
    # migrated from `ckan` canada fork for resource view activities - Jan 2024
    # migrated from `activity` for ckan 2.10 upgrade - June 2024
    object_id_validators.update({
        'new resource view': 'package_id_exists',
        'changed resource view': 'package_id_exists',
        'deleted resource view': 'package_id_exists',
    })


def configure():
    """
    Set initial configuration values after the app stack has been setup
    but prior to requests, this happens after IConfigurer::update_config

    Monkey-patch datastore_upsert to use a temporary database table
    during the transaction to have access to user information.
    """
    # FIXME: monkey-patch datastore upsert_data
    original_upsert_data = db.upsert_data

    def patched_upsert_data(context: Context, data_dict: DataDict) -> Any:
        with datastore_create_temp_user_table(context):
            try:
                return original_upsert_data(context, data_dict)
            except ValidationError as e:
                # reformat tab-delimited error as dict
                # type_ignore_reason: incomplete typing
                head, sep, rerr = e.error_dict.get(  # type: ignore
                    'records', [''])[0].partition('\t')  # type: ignore
                rerr = rerr.rstrip('\n')
                if head == 'TAB-DELIMITED' and sep:
                    out = {}
                    it = iter(rerr.split('\t'))
                    for key, error in zip(it, it):
                        out.setdefault(key, []).append(error)
                    e.error_dict['records'] = [out]
                raise e
    if db.upsert_data.__name__ == 'upsert_data':
        db.upsert_data = patched_upsert_data

    # register custom frictionless plugin
    system.register('canada-validation', CanadaValidationPlugin())


def _wet_pager_admin_url_generator(page: int, partial: Optional[str] = None,
                                   **kwargs: Any) -> str:
    pargs = []
    pargs.append(request.endpoint)
    kwargs['page'] = page
    return h.url_for(*pargs, **kwargs)


def _wet_pager(self: core_helpers.Page, *args: Any, **kwargs: Any):
    # a custom pagination method, because CKAN doesn't
    # expose the pagination to the templates,
    # and instead hardcodes the pagination html in helpers.py
    kwargs.update(
        format="<ul class='pagination'>$link_previous ~2~ $link_next</ul>",
        symbol_previous=core_helpers._('Previous'),
        symbol_next=core_helpers._('Next'),
        curpage_attr={'class': 'active'}
    )

    # pager links fix for ckan-admin/publish route
    if has_request_context() and 'ckan-admin/publish' in request.url:
        self._url_generator = _wet_pager_admin_url_generator

    return super(core_helpers.Page, self).pager(*args, **kwargs)


def _SI_number_span_close(number: Union[str, int]):
    ''' outputs a span with the number in SI unit eg 14700 -> 14.7k '''
    number = int(number)
    if number < 1000:
        output = h.literal('<span>')
    else:
        output = h.literal(
            '<span title="' + formatters.localised_number(number) + '">')
    return output + formatters.localised_SI_number(number) + h.literal('</span>')


# Monkey Patched to inlude the 'list-group-item' class
# TODO: Clean up and convert to proper HTML templates
def build_nav_main(*args: Any):
    ''' build a set of menu items.

    args: tuples of (menu type, title) eg ('login', _('Login'))
    outputs <li><a href="...">title</a></li>
    '''
    output = ''
    for item in args:
        menu_item, title = item[:2]
        if len(item) == 3 and not core_helpers.check_access(item[2]):
            continue
        output += core_helpers._make_menu_item(
            menu_item, title, class_='list-group-item')
    return output