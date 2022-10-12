from ckan.plugins.toolkit import (
    get_action, _, h, c, check_access, aslist, request, render
)

from ckan.views.dataset import EditView as DatasetEditView
from ckan.views.resource import EditView as ResourceEditView
from ckan.views.resource import CreateView as ResourceCreateView
from ckan.authz import is_sysadmin
from ckan.logic import parse_params

from ckanext.recombinant.datatypes import canonicalize
from ckanext.recombinant.tables import get_chromo
from ckanext.recombinant.errors import RecombinantException

from ckanapi import LocalCKAN, NotAuthorized, ValidationError

from flask import Blueprint

from ckanext.canada.urlsafe import url_part_unescape

canada_views = Blueprint('canada', __name__)


class IntentionalServerError(Exception):
    pass


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


class CanadaResourceCreateView(ResourceCreateView):
    def post(self, package_type, id):
        response = super(CanadaResourceCreateView, self).post(package_type, id)
        if hasattr(response, 'status_code'):
            if response.status_code == 200 or response.status_code == 302:
                h.flash_success(_(u'Resource added.'))
        return response


@canada_views.route('/500', methods=['GET'])
def fivehundred():
    raise IntentionalServerError()



def _get_form_full_text_choices(field_name, chromo):
    for field in chromo['fields']:
        if field['datastore_id'] == field_name and \
                field.get('form_full_text_choices', False):
            return True
    return False


@canada_views.route('/create-pd-record/<owner_org>/<resource_name>', methods=['GET', 'POST'])
def create_pd_record(owner_org, resource_name):
    lc = LocalCKAN(username=c.user)

    try:
        chromo = h.recombinant_get_chromo(resource_name)
        rcomb = lc.action.recombinant_show(
            owner_org=owner_org,
            dataset_type=chromo['dataset_type'])
        [res] = [r for r in rcomb['resources'] if r['name'] == resource_name]

        check_access(
            'datastore_upsert',
            {'user': c.user, 'auth_user_obj': c.userobj},
            {'resource_id': res['id']})
    except NotAuthorized:
        return abort(403, _('Unauthorized'))

    choice_fields = {
        f['datastore_id']: [
            {'value': k,
             'label': k + ': ' + v if _get_form_full_text_choices(f['datastore_id'], chromo) else v
             } for (k, v) in f['choices']]
        for f in h.recombinant_choice_fields(resource_name)}

    pk_fields = aslist(chromo['datastore_primary_key'])

    if request.method == 'POST':
        post_data = parse_params(request.form, ignore_keys=['save'])

        if 'cancel' in post_data:
            return h.redirect_to(
                'recombinant.preview_table',
                resource_name=resource_name,
                owner_org=rcomb['owner_org'],
                )

        data, err = _clean_check_type_errors(
            post_data,
            chromo['fields'],
            pk_fields,
            choice_fields)
        try:
            lc.action.datastore_upsert(
                resource_id=res['id'],
                method='insert',
                records=[{k: None if k in err else v for (k, v) in data.items()}],
                dry_run=bool(err))
        except ValidationError as ve:
            if 'records' in ve.error_dict:
                err = dict({
                    k: [_(e) for e in v]
                    for (k, v) in ve.error_dict['records'][0].items()
                }, **err)
            elif ve.error_dict.get('info', {}).get('pgcode', '') == '23505':
                err = dict({
                    k: [_("This record already exists")]
                    for k in pk_fields
                }, **err)

        if err:
            return render('recombinant/create_pd_record.html',
                          extra_vars={
                              'data': data,
                              'resource_name': resource_name,
                              'chromo_title': chromo['title'],
                              'choice_fields': choice_fields,
                              'owner_org': rcomb['owner_org'],
                              'pkg_dict': {},  # prevent rendering error on parent template
                              'errors': err,
                          })

        h.flash_notice(_(u'Record Created'))

        return h.redirect_to(
            'recombinant.preview_table',
            resource_name=resource_name,
            owner_org=rcomb['owner_org'],
        )

    return render('recombinant/create_pd_record.html',
                  extra_vars={
                      'data': {},
                      'resource_name': resource_name,
                      'chromo_title': chromo['title'],
                      'choice_fields': choice_fields,
                      'owner_org': rcomb['owner_org'],
                      'pkg_dict': {},  # prevent rendering error on parent template
                      'errors': {},
                  })


@canada_views.route('/update-pd-record/<owner_org>/<resource_name>/<pk>', methods=['GET', 'POST'])
def update_pd_record(owner_org, resource_name, pk):
    pk = [url_part_unescape(p) for p in pk.split(',')]

    lc = LocalCKAN(username=c.user)

    try:
        chromo = h.recombinant_get_chromo(resource_name)
        rcomb = lc.action.recombinant_show(
            owner_org=owner_org,
            dataset_type=chromo['dataset_type'])
        [res] = [r for r in rcomb['resources'] if r['name'] == resource_name]

        check_access(
            'datastore_upsert',
            {'user': c.user, 'auth_user_obj': c.userobj},
            {'resource_id': res['id']})
    except NotAuthorized:
        abort(403, _('Unauthorized'))

    choice_fields = {
        f['datastore_id']: [
            {'value': k,
             'label': k + ': ' + v if _get_form_full_text_choices(f['datastore_id'], chromo) else v
             } for (k, v) in f['choices']]
        for f in h.recombinant_choice_fields(resource_name)}

    pk_fields = aslist(chromo['datastore_primary_key'])
    pk_filter = dict(zip(pk_fields, pk))

    records = lc.action.datastore_search(
        resource_id=res['id'],
        filters=pk_filter)['records']
    if len(records) == 0:
        abort(404, _('Not found'))
    if len(records) > 1:
        abort(400, _('Multiple records found'))
    record = records[0]

    if request.method == 'POST':
        post_data = parse_params(request.form, ignore_keys=['save'] + pk_fields)

        if 'cancel' in post_data:
            return h.redirect_to(
                'recombinant.preview_table',
                resource_name=resource_name,
                owner_org=rcomb['owner_org'],
                )

        data, err = _clean_check_type_errors(
            post_data,
            chromo['fields'],
            pk_fields,
            choice_fields)
        # can't change pk fields
        for f_id in data:
            if f_id in pk_fields:
                data[f_id] = record[f_id]
        try:
            lc.action.datastore_upsert(
                resource_id=res['id'],
                #method='update',    FIXME not raising ValidationErrors
                records=[{k: None if k in err else v for (k, v) in data.items()}],
                dry_run=bool(err))
        except ValidationError as ve:
            try:
                err = dict({
                    k: [_(e) for e in v]
                    for (k, v) in ve.error_dict['records'][0].items()
                }, **err)
            except AttributeError as e:
                raise ve

        if err:
            return render('recombinant/update_pd_record.html',
                extra_vars={
                    'data': data,
                    'resource_name': resource_name,
                    'chromo_title': chromo['title'],
                    'choice_fields': choice_fields,
                    'pk_fields': pk_fields,
                    'owner_org': rcomb['owner_org'],
                    'pkg_dict': {},  # prevent rendering error on parent template
                    'errors': err,
                    })

        h.flash_notice(_(u'Record %s Updated') % u','.join(pk) )

        return h.redirect_to(
            'recombinant.preview_table',
            resource_name=resource_name,
            owner_org=rcomb['owner_org'],
            )

    data = {}
    for f in chromo['fields']:
        if not f.get('import_template_include', True):
            continue
        val = record[f['datastore_id']]
        data[f['datastore_id']] = val

    return render('recombinant/update_pd_record.html',
        extra_vars={
            'data': data,
            'resource_name': resource_name,
            'chromo_title': chromo['title'],
            'choice_fields': choice_fields,
            'pk_fields': pk_fields,
            'owner_org': rcomb['owner_org'],
            'pkg_dict': {},  # prevent rendering error on parent template
            'errors': {},
            })



@canada_views.route('/recombinant/<resource_name>', methods=['GET'])
def type_redirect(resource_name):
    orgs = h.organizations_available('read')

    if not orgs:
        abort(404, _('No organizations found'))
    try:
        chromo = get_chromo(resource_name)
    except RecombinantException:
        abort(404, _('Recombinant resource_name not found'))

    # custom business logic
    if is_sysadmin(c.user):
        return h.redirect_to(h.url_for('recombinant.preview_table',
                                  resource_name=resource_name, owner_org='tbs-sct'))
    return h.redirect_to(h.url_for('recombinant.preview_table',
                              resource_name=resource_name, owner_org=orgs[0]['name']))

def _clean_check_type_errors(post_data, fields, pk_fields, choice_fields):
    """
    clean posted data and check type errors, add type error messages
    to errors dict returned. This is required because type errors on any
    field prevent triggers from running so we don't get any other errors
    from the datastore_upsert call.
    :param post_data: form data
    :param fields: recombinant fields
    :param pk_fields: list of primary key field ids
    :param choice_fields: {field id: choices, ...}
    :return: cleaned data, errors
    """
    data = {}
    err = {}

    for f in fields:
        f_id = f['datastore_id']
        if not f.get('import_template_include', True):
            continue
        else:
            val = post_data.get(f['datastore_id'], '')
            if isinstance(val, list):
                val = u','.join(val)
            val = canonicalize(
                val,
                f['datastore_type'],
                primary_key=f['datastore_id'] in pk_fields,
                choice_field=f_id in choice_fields)
            if val:
                if f['datastore_type'] in ('money', 'numeric'):
                    try:
                        decimal.Decimal(val)
                    except decimal.InvalidOperation:
                        err[f['datastore_id']] = [_(u'Number required')]
                elif f['datastore_type'] == 'int':
                    try:
                        int(val)
                    except ValueError:
                        err[f['datastore_id']] = [_(u'Integer required')]
            data[f['datastore_id']] = val

    return data, err
