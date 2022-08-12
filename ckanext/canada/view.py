from webob.exc import HTTPFound
import logging

from ckan.common import _
from ckantoolkit import (
    c,
    h
)

from ckan.views.dataset import EditView as DatasetEditView
from ckan.views.resource import EditView as ResourceEditView

log = logging.getLogger(__name__)


class CanadaDatasetEditView(DatasetEditView):
    def post(self, package_type, id):
        try:
            response = super(CanadaDatasetEditView, self).post(package_type, id)
        except HTTPFound:
            if c.pkg_dict['type'] == 'prop':
                h.flash_success(_(u'The status has been added / updated for this suggested  dataset. This update will be reflected on open.canada.ca shortly.'))
            raise


class CanadaResourceEditView(ResourceEditView):
    def post(self, package_type, id, resource_id):
        try:
            response = super(CanadaResourceEditView, self).post(package_type, id, resource_id)
        except HTTPFound:
            h.flash_success(_(u'Resource updated.'))
            raise