from __future__ import absolute_import

from ckan import plugins

from ckanext.harvest.interfaces import IHarvester

PORTAL_SYNC_ID = 'portal_sync_harvester'


class PortalSync(plugins.SingletonPlugin):
    """
    Harvester class to sync Portal Datasets, Resources, Views,
    and DataStores from the Registry.
    """
    plugins.implements(IHarvester)

    def info(self):
        return {
            'name': 'portal_sync',
            'title': plugins.toolkit._('Portal Sync'),
            'description': plugins.toolkit._('Syncs Datasets, Resources, Views, and DataStores from the Registry to the Portal.'),
            'form_config_interface': 'Text'
        }
