from webob.exc import HTTPFound

from ckan.logic import get_action
from ckan.common import _
from ckantoolkit import (
    c,
    h
)

from ckan.views.dataset import EditView as DatasetEditView
from ckan.views.resource import EditView as ResourceEditView


class CanadaDatasetEditView(DatasetEditView):
    def post(self, package_type, id):
        try:
            return super(CanadaDatasetEditView, self).post(package_type, id)
        except HTTPFound:
            context = self._prepare(id)
            pkg_dict = get_action(u'package_show')(
                dict(context, for_view=True), {
                    u'id': id
                }
            )
            if pkg_dict['type'] == 'prop':
                h.flash_success(_(u'The status has been added / updated for this suggested  dataset. This update will be reflected on open.canada.ca shortly.'))
            else:
                h.flash_success(_(u'Dataset updated (canada view).'))


class CanadaResourceEditView(ResourceEditView):
    def post(self, package_type, id, resource_id):
        try:
            return super(CanadaResourceEditView, self).post(package_type, id, resource_id)
        except HTTPFound:
             h.flash_success(_(u'Resource updated.'))
