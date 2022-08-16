from ckan.logic import get_action
from ckan.common import _
from ckantoolkit import h

from ckan.views.dataset import EditView as DatasetEditView
from ckan.views.resource import EditView as ResourceEditView


class CanadaDatasetEditView(DatasetEditView):
    def post(self, package_type, id):
        response = super(CanadaDatasetEditView, self).post(package_type, id)
        if hasattr(response, 'status_code'):
            if response.status_code == 200 or response.status_code == 302:
                context = self._prepare(id)
                pkg_dict = get_action(u'package_show')(
                    dict(context, for_view=True), {
                        u'id': id
                    }
                )
                if pkg_dict['type'] == 'prop':
                    h.flash_success(_(u'The status has been added / updated for this suggested  dataset. This update will be reflected on open.canada.ca shortly.'))
                else:
                    h.flash_success(_(u'Dataset updated.'))
        return response


class CanadaResourceEditView(ResourceEditView):
    def post(self, package_type, id, resource_id):
        response = super(CanadaResourceEditView, self).post(package_type, id, resource_id)
        if hasattr(response, 'status_code'):
            if response.status_code == 200 or response.status_code == 302:
                 h.flash_success(_(u'Resource updated.'))
        return response

