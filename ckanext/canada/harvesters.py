from __future__ import absolute_import

from typing import Union, Optional

from os.path import isfile
import subprocess
import datetime
import json
from configparser import ConfigParser, NoOptionError

from sqlalchemy import exists, and_
from sqlalchemy.orm import contains_eager

from ckan import plugins
from ckan import model
from ckan.logic.validators import isodate

from ckanext.datastore.backend.postgres import _get_engine_from_url

from ckanext.harvest.interfaces import IHarvester
from ckanext.harvest.model import HarvestJob, HarvestObject, HarvestObjectExtra, HarvestGatherError, HarvestObjectError

from ckanapi import LocalCKAN

import logging
log = logging.getLogger(__name__)


PORTAL_SYNC_ID = 'portal_sync_harvester'
HARVESTER_ID = 'portal_sync'

SYNC_DATASET_TYPES = ['info', 'dataset', 'prop']

SYNC_PACKAGE_TRIM_FIELDS = ['extras', 'metadata_modified', 'metadata_created',
    'revision_id', 'revision_timestamp', 'organization',
    'version', 'tracking_summary',
    'tags', # not used
    'num_tags', 'num_resources', 'maintainer',
    'isopen', 'relationships_as_object', 'license_title',
    'license_title_fra', 'license_url_fra', 'license_url',
    'author',
    'groups', # not used
    'relationships_as_subject', 'department_number',
    # FIXME: remove these when we can:
    'resource_type',
    'creator_user_id']

SYNC_RESOURCE_TRIM_FIELDS = ['package_id', 'revision_id',
    'revision_timestamp', 'cache_last_updated',
    'webstore_last_updated', 'state',
    'description', 'tracking_summary', 'mimetype_inner',
    'mimetype', 'cache_url', 'created', 'webstore_url',
    'position', 'metadata_modified']


class PortalSync(plugins.SingletonPlugin):
    """
    Harvester class to sync Portal Datasets, Resources, Views,
    and DataStores from the Registry.
    """
    plugins.implements(IHarvester)


    _save_gather_error = HarvestGatherError.create
    _save_object_error = HarvestObjectError.create


    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        registry_ini = plugins.toolkit.config.get('ckanext.canada.portal_sync.registry_ini')
        portal_ini = plugins.toolkit.config.get('ckanext.canada.portal_sync.portal_ini')
        if not registry_ini:
            raise Exception('ckanext.canada.portal_sync.registry_ini not defined')
        if not isfile(registry_ini):
            raise Exception('Cannot find file %s, defined from ckanext.canada.portal_sync.registry_ini' % registry_ini)
        if not portal_ini:
            raise Exception('ckanext.canada.portal_sync.portal_ini not defined')
        if not isfile(portal_ini):
            raise Exception('Cannot find file %s, defined from ckanext.canada.portal_sync.portal_ini' % portal_ini)

        registry_config = ConfigParser()
        registry_config.read(registry_ini)
        try:
            registry_datastore_url = registry_config.get('app:main', 'ckan.datastore.write_url')
        except NoOptionError:
            raise Exception('Cannot find ckan.datastore.write_url in app:main section of Registry INI')
        self.registry_datastore_url = str(_get_engine_from_url(registry_datastore_url).url)  # ensure that this is actually a DS database
        portal_config = ConfigParser()
        portal_config.read(portal_ini)
        try:
            portal_datastore_url = portal_config.get('app:main', 'ckan.datastore.write_url')
        except NoOptionError:
            raise Exception('Cannot find ckan.datastore.write_url in app:main section of Portal INI')
        self.portal_datastore_url = str(_get_engine_from_url(portal_datastore_url).url)  # ensure that this is actually a DS database

        #FIXME: figure out how to get the data from and to the Portal in fetch_stage and import_stage
        self.registry = LocalCKAN()
        self.portal = LocalCKAN()


    @classmethod
    def last_error_free_job(cls, harvest_job):
        """Look for jobs with no gather errors"""
        jobs = (model.Session.query(HarvestJob)
                .filter(HarvestJob.source == harvest_job.source)
                .filter(HarvestJob.gather_started != None)  # noqa: E711
                .filter(HarvestJob.status == 'Finished')
                .filter(HarvestJob.id != harvest_job.id)
                .filter(
            ~exists().where(
                HarvestGatherError.harvest_job_id == HarvestJob.id))
                .outerjoin(HarvestObject,
                           and_(HarvestObject.harvest_job_id == HarvestJob.id,
                                HarvestObject.current == False,  # noqa: E712
                                HarvestObject.report_status != 'not modified'))
                .options(contains_eager(HarvestJob.objects))
                .order_by(HarvestJob.gather_started.desc()))
        # now check them until we find one with no fetch/import errors
        # if objects count is 0, job was error free
        for job in jobs:
            if len(job.objects) == 0:
                return job


    def info(self):
        return {
            'name': HARVESTER_ID,
            'title': 'Portal Sync',
            'title_translated': {
                'en': 'Portal Sync',
                'fr': 'FR Portal Sync FR',
            },
            'description': 'Syncs Datasets, Resources, Views, and DataStores from the Registry to the Portal.',
            'description_translated': {
                'en': 'Syncs Datasets, Resources, Views, and DataStores from the Registry to the Portal.',
                'fr': 'FR Syncs Datasets, Resources, Views, and DataStores from the Registry to the Portal. FR',
            },
            'form_config_interface': 'Text'
        }


    def validate_config(self, config):
        return {}


    def gather_stage(self, harvest_job):
        '''
        The gather stage will receive a HarvestJob object and will be
        responsible for:
            - gathering all the necessary objects to fetch on a later.
              stage (e.g. for a CSW server, perform a GetRecords request)
            - creating the necessary HarvestObjects in the database, specifying
              the guid and a reference to its job. The HarvestObjects need a
              reference date with the last modified date for the resource, this
              may need to be set in a different stage depending on the type of
              source.
            - creating and storing any suitable HarvestGatherErrors that may
              occur.
            - returning a list with all the ids of the created HarvestObjects.
            - to abort the harvest, create a HarvestGatherError and raise an
              exception. Any created HarvestObjects will be deleted.

        NOTE:
        PortalSync: Gathers packages via changed_packages_activity_timestamp_since.
                    Saves HarvestObjects with the content of the Source Package, Resource Views, and DataDictionaries.

        :param harvest_job: HarvestJob object
        :returns: A list of HarvestObject ids
        '''
        log.info('In PortalSync gather_stage (%s)', harvest_job.source.url)

        # Request only the activity since last successful run
        last_error_free_job = self.last_error_free_job(harvest_job)
        log.info('Last error-free job: %r', last_error_free_job)
        last_time = last_error_free_job.gather_started

        # Note: SOLR works in UTC, and gather_started is also UTC, so
        # this should work as long as local and remote clocks are
        # relatively accurate. Going back a little earlier, just in case.
        get_changes_since = (last_time - datetime.timedelta(hours=1)).isoformat()
        log.info('Searching for activity since: %s UTC', get_changes_since)

        data = self.registry.action.changed_packages_activity_timestamp_since(since_time=last_time.isoformat())
        if not data:
            # There is no activity since last successful run
            return []

        registry_packages = []

        for result in data:
            package_id = result['package_id']
            try:
                source_package = self.registry.action.package_show(id=package_id)
            except plugins.toolkit.ObjectNotFound:
                log.info("Package %s not found in Registry database.", package_id)
                self._save_gather_error("Package (%s) not found in Registry database.", package_id)
                pass
            else:
                source_package = self._get_datastore_and_views(source_package, ckan_instance=self.registry, stage='GATHER')
                registry_packages.append(source_package)

        harvest_object_ids = []

        for registry_package in registry_packages:
            source_package = registry_package.copy()

            if source_package and (source_package.get('state') == 'deleted' or source_package.get('type') not in SYNC_DATASET_TYPES):
                # Do not sync deleted packages or packages that are NOT type: 'info', 'dataset', 'prop'
                source_package = None

            _trim_package_for_sync(source_package)

            if source_package:
                now = datetime.now()
                if source_package.get('ready_to_publish') == 'false':
                    source_package = None
                    log.info("Package %s marked not ready to publish.", source_package['id'])
                elif not source_package.get('portal_release_date'):
                    source_package = None
                    log.info("Package %s release date not set.", source_package['id'])
                elif isodate(source_package.get('portal_release_date'), None) > now:
                    source_package = None
                    log.info("Package %s release date in future.", source_package['id'])
                else:
                    # Portal packages are public, do this to match
                    source_package['private'] = False

            log.info('Creating HarvestObject for package %s', registry_package['id'])
            obj = HarvestObject(guid=registry_package['id'],
                                harvest_source_id=harvest_job.source.id,
                                harvest_job_id=harvest_job.id,
                                job=harvest_job,
                                package_id=registry_package['id'],
                                content=json.dumps(source_package) if source_package else None)
            obj.save()
            harvest_object_ids.append(obj.id)

        return harvest_object_ids


    def fetch_stage(self, harvest_object):
        '''
        The fetch stage will receive a HarvestObject object and will be
        responsible for:
            - getting the contents of the remote object (e.g. for a CSW server,
              perform a GetRecordById request).
            - saving the content in the provided HarvestObject.
            - creating and storing any suitable HarvestObjectErrors that may
              occur.
            - returning True if everything is ok (ie the object should now be
              imported), "unchanged" if the object didn't need harvesting after
              all (ie no error, but don't continue to import stage) or False if
              there were errors.

        NOTE:
        PortalSync: Uses LocalCKAN instances of the Registry and Portal to check what needs syncing.
                    Will check package metadata, resource metadata, resource views, and datastores/data dictionaries.

        :param harvest_object: HarvestObject object
        :returns: True if successful, 'unchanged' if nothing to import after
                  all, False if not successful
        '''
        log.info('In PortalSync fetch_stage (%s)', harvest_object.guid)

        # FIXME: in this stage, we have to get the package from the Portal (if it exists).
        #        but we have to save the HarvestObjectErrors to the Registry DB. HOW??

        source_package_id = harvest_object.guid
        source_package = None

        if harvest_object.content is not None:
            try:
                source_package = json.loads(harvest_object.content)
            except (TypeError, ValueError) as e:
                self._save_object_error('Invalid source package (%s) JSON with error: %s' % (harvest_object.guid, str(e)))
                return False  # False if not successful

        target_deleted = False
        target_package = None

        try:
            target_package = self.portal.call_action('package_show', {'id': source_package_id})
        except (plugins.toolkit.ObjectNotFound, plugins.toolkit.NotAuthorized):
            target_package = None
            pass

        if target_package and target_package.get('state') == 'deleted':
            target_package = None
            target_deleted = True

        target_package = self._get_datastore_and_views(target_package, self.portal, stage='FETCH')
        _trim_package_for_sync(target_package)

        if target_package is None and source_package is None:
            log.info('Package %s not found on Registry or Portal. No Change.', source_package_id)
            return 'unchanged'  # 'unchanged' if nothing to import
        elif target_deleted:
            log.info('Package %s deleted on Portal. Going to undelete it on Portal.', source_package_id)
            obj = HarvestObjectExtra(harvest_object_id=harvest_object.id, key='sync_action', value='package_update')
            obj.save()
            # Use Registry resource file hashes
            file_hashes = {}
            for _resource in source_package['resources']:
                file_hashes[_resource['id']] = _resource.get('hash')
            obj = HarvestObjectExtra(harvest_object_id=harvest_object.id, key='resource_file_hashes', value=json.dumps(file_hashes))
            obj.save()
            return True  # True if successful
        elif target_package is None:
            log.info('Package %s not found on Portal. Going to create it on Portal.', source_package_id)
            obj = HarvestObjectExtra(harvest_object_id=harvest_object.id, key='sync_action', value='package_create')
            obj.save()
            return True  # True if successful
        elif source_package is None:
            log.info('Package %s deleted on Registry or is not a Portal Package Type. Going to delete it on Portal.', source_package_id)
            obj = HarvestObjectExtra(harvest_object_id=harvest_object.id, key='sync_action', value='package_delete')
            obj.save()
            return True  # True if successful
        elif source_package == target_package:
            log.info('Package %s has no differences between Registry and Portal. No Change.', source_package_id)
            return 'unchanged'  # 'unchanged' if nothing to import
        else:
            log.info('Package %s needs updating Portal. Going to update it on Portal.', source_package_id)
            obj = HarvestObjectExtra(harvest_object_id=harvest_object.id, key='sync_action', value='package_update')
            obj.save()
            # Use Portal resource file hashes
            file_hashes = {}
            for _resource in target_package['resources']:
                file_hashes[_resource['id']] = _resource.get('hash')
            obj = HarvestObjectExtra(harvest_object_id=harvest_object.id, key='resource_file_hashes', value=json.dumps(file_hashes))
            obj.save()
            return True  # True if successful


    def import_stage(self, harvest_object):
        '''
        The import stage will receive a HarvestObject object and will be
        responsible for:
            - performing any necessary action with the fetched object (e.g.
              create, update or delete a CKAN package).
              Note: if this stage creates or updates a package, a reference
              to the package should be added to the HarvestObject.
            - setting the HarvestObject.package (if there is one)
            - setting the HarvestObject.current for this harvest:
               - True if successfully created/updated
               - False if successfully deleted
            - setting HarvestObject.current to False for previous harvest
              objects of this harvest source if the action was successful.
            - creating and storing any suitable HarvestObjectErrors that may
              occur.
            - creating the HarvestObject - Package relation (if necessary)
            - returning True if the action was done, "unchanged" if the object
              didn't need harvesting after all or False if there were errors.

        NB You can run this stage repeatedly using 'paster harvest import'.

        NOTE:
        PortalSync: Performs the actual create/update/delete actions on the Portal.

        :param harvest_object: HarvestObject object
        :returns: True if the action was done, "unchanged" if the object didn't
                  need harvesting after all or False if there were errors.
        '''
        log.info('In PortalSync import_stage (%s)', harvest_object.guid)

        # FIXME: in this stage, we have to post the package to the Portal.
        #        but we have to save the HarvestObjectErrors to the Registry DB. HOW??

        source_package_id = harvest_object.guid
        source_package = None

        if harvest_object.content is not None:
            try:
                source_package = json.loads(harvest_object.content)
            except (TypeError, ValueError) as e:
                self._save_object_error('Invalid source package (%s) JSON with error: %s' % (harvest_object.guid, str(e)))
                return False  # False if there were errors

        action = None
        resource_file_hashes = {}
        for extra in harvest_object.extras:
            if extra.key == 'sync_action':
                action = extra.value
            if extra.key == 'resource_file_hashes':
                try:
                    resource_file_hashes = json.loads(extra.value)
                except (TypeError, ValueError):
                    resource_file_hashes = {}
                    pass

        if not action:
            self._save_object_error('Could not find action for package %s' % harvest_object.guid)
            return False  # False if there were errors

        if source_package is None:
            # is delete action at this point
            try:
                self.portal.call_action(action, {'id': source_package_id})
                # Flag the other objects linking to this package as not current anymore
                model.Session.query(HarvestObject).filter(
                    HarvestObject.package_id == source_package_id).update({"current": False})
                harvest_object.package_id = source_package_id
                harvest_object.current = False  # False if successfully deleted
                harvest_object.save()
                model.Session.commit()
                return True  # True if the action was done
            except Exception as e:
                self._save_object_error('Could not delete package (%s) from the Portal with error: %s' % (harvest_object.guid, str(e)))
                return False  # False if there were errors

        try:
            self.portal.call_action(action, source_package)
            # "Note: if this stage creates or updates a package, a reference to the package should be added to the HarvestObject."
            # NOTE: because the package is on the Portal, we are not adding the database reference here.
            self._sync_datastore_and_views(source_package, resource_file_hashes)
            # Flag the other objects linking to this package as not current anymore
            model.Session.query(HarvestObject).filter(
                HarvestObject.package_id == source_package_id).update({"current": False})
            harvest_object.package_id = source_package_id
            harvest_object.current = True  # True if successfully created/updated
            harvest_object.save()
            model.Session.commit()
            return True  # True if the action was done
        except Exception as e:
            self._save_object_error('Could not %s package (%s) on the Portal with error: %s' % (action, harvest_object.guid, str(e)))
            return False  # False if there were errors


    def _get_datastore_and_views(self, package: Union[dict, None], ckan_instance: LocalCKAN, stage: Optional[Union[str, None]]=None):
        """
        Adds DataDictionaries, Views Lists, and File Hashes to the package's resources.

        Provide a LocalCKAN instance to ckan_instance, can be used for Registry and Portal.
        """
        if package and 'resources' in package:
            for resource in package['resources']:
                # check if resource exists in datastore
                if resource['datastore_active']:
                    log.info("DataStore is active for %s" % resource['id'])
                    log.info("  Getting resource views and DataStore fields...")
                    try:
                        table = ckan_instance.call_action('datastore_search',
                                                          {'resource_id': resource['id'],
                                                           'limit': 0})
                        if table:
                            # add hash, views and data dictionary
                            package[resource['id']] = {
                                "hash": resource.get('hash'),
                                "views": ckan_instance.call_action('resource_view_list',
                                                                   {'id': resource['id']}),
                                "data_dict": self._get_datastore_dictionary(ckan_instance, resource['id']),
                            }
                    except plugins.toolkit.ObjectNotFound:
                        # we can consider this an error as datastore_search SHOULD return something if datastore_active
                        # and resource_view_list should always return something or empty list if the resource exists.
                        log.info("  WARNING: Did not find resource views or DataStore fields...")
                        if stage == 'GATHER':
                            self._save_gather_error('Could not find resource views or DataStore fields on the Registry for resource %s (pkg: %s)' % (resource['id'], package['id']))
                        elif stage == 'FETCH':
                            self._save_object_error('Could not find resource views or DataStore fields on the Portal for resource %s (pkg: %s)' % (resource['id'], package['id']))
                        pass
                    except plugins.toolkit.ValidationError as e:
                        # this is absolutely an error as we should not be getting ValidationError, but it can happen
                        # sometimes because of our ckanext-validation and xloader workflow on the Registry.
                        log.info("  WARNING: Invalid DataStore or Resource View, with error: %s" % str(e))
                        if stage == 'GATHER':
                            self._save_gather_error('Failed to get resource views or DataStore fields on the Registry for resource %s (pkg: %s) with error: %s' % (resource['id'], package['id'], str(e)))
                        elif stage == 'FETCH':
                            self._save_object_error('Failed to get resource views or DataStore fields on the Portal for resource %s (pkg: %s) with error: %s' % (resource['id'], package['id'], str(e)))
                        pass
                else:
                    log.info("DataStore is inactive for %s" % resource['id'])
                    log.info("  Only getting resource views...")
                    resource_views = ckan_instance.call_action('resource_view_list',
                                                               {'id': resource['id']})
                    if resource_views:
                        package[resource['id']] = {"views": resource_views}
        return package


    def _sync_datastore_and_views(self, source_package: Union[dict, None], resource_hashes: dict):
        """
        Create DataStore table and views for each resource of the package.
        """
        action = ''
        for source_resource in source_package['resources']:
            res_id = source_resource['id']
            if res_id in source_package.keys():
                if 'data_dict' in source_package[res_id].keys():
                    self._sync_datastore(source_resource, source_package[res_id], resource_hashes)
                if 'views' in source_package[res_id].keys():
                    self._sync_resource_views(source_resource, source_package[res_id])
        return action


    def _sync_datastore(self, source_resource: Union[dict, None], source_resource_details: Union[dict, None], resource_hashes: dict):
        """
        Syncs Registry DataStore and DataDictionary to the Portal.
        """
        try:
            self.portal.call_action('datastore_search', {'resource_id': source_resource['id'], 'limit': 0})
            if resource_hashes.get(source_resource['id']) \
                    and resource_hashes.get(source_resource['id']) == source_resource.get('hash')\
                    and self._get_datastore_dictionary(self.portal, source_resource['id']) == source_resource_details['data_dict']:
                log.info('  File hash and Data Dictionary has not changed, skipping DataStore for %s...', source_resource['id'])
                return
            else:
                self.portal.call_action('datastore_delete', {"id": source_resource['id'], "force": True})
                log.info('  datastore-deleted for ', source_resource['id'])
        except plugins.toolkit.ObjectNotFound:
            # not an issue, resource does not exist in datastore
            log.info('  DataStore does not exist for resource %s...trying to create it...', source_resource['id'])
            pass

        self.portal.call_action('datastore_create',
                                {"resource_id": source_resource['id'],
                                 "fields": source_resource_details['data_dict'],
                                 "force": True})

        log.info('  datastore-created for ', source_resource['id'])

        # load data
        cmd1 = subprocess.Popen(['pg_dump', self.registry_datastore_url, '-a', '-t', source_resource['id']], stdout=subprocess.PIPE)
        cmd2 = subprocess.Popen(['psql', self.portal_datastore_url], stdin=cmd1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = cmd2.communicate()
        log.info('  data-loaded' if not err else ' data-load-failed')
        if source_resource_details['data_dict']:
            log.info('    Using DataStore fields:')
            for field in source_resource_details['data_dict']:
                log.info('      %s', field['id'])
        else:
            log.info('    There are no DataStore fields!!!')


    def _sync_resource_views(self, source_resource: Union[dict, None], source_resource_details: Union[dict, None]):
        """
        Syncs Registry Resource Views to the Portal.
        """
        target_views = self.portal.call_action('resource_view_list', {'id': source_resource['id']})
        for src_view in source_resource_details['views']:
            view_action = 'resource_view_create'
            for target_view in target_views:
                if target_view['id'] == src_view['id']:
                    view_action = None if target_view == src_view else 'resource_view_update'

            if view_action:
                try:
                    self.portal.call_action(view_action, src_view)
                    log.info('  %s for view %s for resource %s', view_action, src_view['id'], source_resource['id'])
                except plugins.toolkit.ValidationError as e:
                    log.info('  %s failed for view %s for resource', view_action, src_view['id'], source_resource['id'])
                    log.info('    Failed with ValidationError: %s', e.error_dict)
                    pass

        for target_view in target_views:
            to_delete = True
            for src_view in source_resource_details['views']:
                if target_view['id'] == src_view['id']:
                    to_delete = False
                    break
            if to_delete:
                view_action = 'resource_view_delete'
                self.portal.call_action(view_action, {'id':target_view['id']})
                log.info('  %s for view %s for resource', view_action, src_view['id'], source_resource['id'])


    def _get_datastore_dictionary(self, ckan_instance: LocalCKAN, resource_id: str):
        """
        Return the data dictionary info for a resource.
        """
        try:
            return [
                f for f in ckan_instance.call_action('datastore_search', {
                        u'resource_id': resource_id,
                        u'limit': 0,
                        u'include_total': False})['fields']
                if not f['id'].startswith(u'_')]
        except (plugins.toolkit.ObjectNotFound, plugins.toolkit.NotAuthorized):
            return []


def _trim_package_for_sync(pkg):
    """
    Remove keys from pkg that we don't care about when comparing
    or updating/creating packages. Also try to convert types and
    create missing fields that will be present in package_show.
    """
    if not pkg:
        return
    for k in SYNC_PACKAGE_TRIM_FIELDS:
        if k in pkg:
            del pkg[k]
    for r in pkg['resources']:
        for k in SYNC_RESOURCE_TRIM_FIELDS:
            if k in r:
                del r[k]
        if 'datastore_contains_all_records_of_source_file' in r:
            r['datastore_contains_all_records_of_source_file'] = \
                plugins.toolkit.asbool(r['datastore_contains_all_records_of_source_file'])
        if r.get('url_type') == 'upload' and r['url']:
            r['url'] = r['url'].rsplit('/', 1)[-1]
        for k in ['name', 'size']:
            if k not in r:
                r[k] = None
    if 'name' not in pkg or not pkg['name']:
        pkg['name'] = pkg['id']
    if 'type' not in pkg:
        pkg['type'] = 'dataset'
    if 'state' not in pkg:
        pkg['state'] = 'active'
    for k in ['url']:
        if k not in pkg:
            pkg[k] = ''
