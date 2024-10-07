from __future__ import absolute_import

from ckan import plugins

from ckanext.harvest.interfaces import IHarvester
from ckanext.harvest.model import HarvestGatherError, HarvestObjectError

from ckanapi import LocalCKAN

PORTAL_SYNC_ID = 'portal_sync_harvester'
HARVESTER_ID = 'portal_sync'


class PortalSync(plugins.SingletonPlugin):
    """
    Harvester class to sync Portal Datasets, Resources, Views,
    and DataStores from the Registry.
    """
    plugins.implements(IHarvester)


    def _init_config(self):
        self.registry = LocalCKAN()


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
                    Uses LocalCKAN instances of the Registry and Portal to check what needs syncing.
                    Will check package metadata, resource metadata, resource views, and datastores.

        :param harvest_job: HarvestJob object
        :returns: A list of HarvestObject ids
        '''
        return []


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

        :param harvest_object: HarvestObject object
        :returns: True if successful, 'unchanged' if nothing to import after
                  all, False if not successful
        '''
        # Nothing to do here - we got the package dicts in the gather stage
        return True


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
        return 'unchanged'
