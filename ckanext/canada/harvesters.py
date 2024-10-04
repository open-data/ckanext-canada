from __future__ import absolute_import

from ckan import plugins

from ckanext.harvest.interfaces import IHarvester

PORTAL_SYNC_ID = 'portal_sync_harvester'
HARVESTER_ID = 'portal_sync'


class PortalSync(plugins.SingletonPlugin):
    """
    Harvester class to sync Portal Datasets, Resources, Views,
    and DataStores from the Registry.
    """
    plugins.implements(IHarvester)


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
