# -*- coding: utf-8 -*-
from typing import Any, cast
from ckan.types import Context, FlattenKey, FlattenDataDict, FlattenErrorDict

import re
import unicodedata

from six import text_type

from ckan.plugins.toolkit import (
    _,
    h,
    get_action,
    ValidationError,
    ObjectNotFound,
    config,
    get_validator,
    Invalid,
    missing
)
from ckan.lib.navl.validators import StopOnError
from ckan.authz import is_sysadmin
from ckan import model

from ckanext.canada.helpers import may_publish_datasets
import geojson
from geomet import wkt
import json
import uuid
from datetime import datetime

from ckan.lib.helpers import date_str_to_datetime
from ckanext.fluent.validators import fluent_text_output, LANG_SUFFIX
from ckanext.security.resource_upload_validator import (
    validate_upload_type, validate_upload_presence
)

not_empty = get_validator('not_empty')
ignore_missing = get_validator('ignore_missing')

MIN_TAG_LENGTH = 2
MAX_TAG_LENGTH = 140  # because twitter


def protect_portal_release_date(key: FlattenKey,
                                data: FlattenDataDict,
                                errors: FlattenErrorDict,
                                context: Context):
    """
    Ensure the portal_release_date is not changed by an unauthorized user.
    """
    if is_sysadmin(context['user']):
        return
    original = ''
    package = context.get('package')
    if package:
        original = package.extras.get('portal_release_date', '')
    value = data.get(key, '')
    if original == value:
        return

    user = context['user']
    user = model.User.get(user)
    if may_publish_datasets(user):
        return

    if not value:
        # silently replace with the old value when none is sent
        data[key] = original
        return

    errors[key].append("Cannot change value of key from '%s' to '%s'. "
                       'This key is read-only' % (original, value))

    raise StopOnError


def user_read_only(key: FlattenKey,
                   data: FlattenDataDict,
                   errors: FlattenErrorDict,
                   context: Context):
    # sysadmins are free to change fields as they like
    if is_sysadmin(context['user']) and data[key] is not missing:
        return

    assert len(key) == 1, 'only package fields supported user_read_only (not %r)' % key

    package = context.get('package')
    if not package and data[key] is not missing:
        errors[key].append("Only sysadmin may set this value")
        raise StopOnError

    if hasattr(package, key[0]):
        data[key] = getattr(package, key[0])
    elif package:
        data[key] = package.extras.get(key[0], '')


def user_read_only_json(key: FlattenKey,
                        data: FlattenDataDict,
                        errors: FlattenErrorDict,
                        context: Context):
    # sysadmins are free to change fields as they like
    if is_sysadmin(context['user']) and data[key] is not missing:
        return

    assert len(key) == 1, 'only package fields supported user_read_only (not %r)' % key

    package = context.get('package')
    if not package and data[key] is not missing:
        errors[key].append("Only sysadmin may set this value")
        raise StopOnError

    if hasattr(package, key[0]):
        data[key] = json.loads(getattr(package, key[0]))
    elif package and hasattr(package, 'extras'):
        # type_ignore_reason: checking attribute
        data[key] = json.loads(package.extras.get(key[0], 'null'))


def canada_tags(value: Any, context: Context):
    """
    Accept
    - unicode graphical (printable) characters
    - single internal spaces (no double-spaces)

    Reject
    - tags that are too short or too long

    Strip
    - spaces at beginning and end
    """
    value = value.strip()
    if len(value) < MIN_TAG_LENGTH:
        raise Invalid(
            _('Tag "%s" length is less than minimum %s')
            % (value, MIN_TAG_LENGTH))
    if len(value) > MAX_TAG_LENGTH:
        raise Invalid(
            _('Tag "%s" length is more than maximum %i')
            % (value, MAX_TAG_LENGTH))
    if '  ' in value:
        raise Invalid(
            _('Tag "%s" may not contain consecutive spaces') % (value,))

    caution = re.sub(r'[\w ]*', '', value)
    for ch in caution:
        category = unicodedata.category(ch)
        if category.startswith('C'):
            raise Invalid(
                _('Tag "%s" may not contain unprintable character U+%04x')
                % (value, ord(ch)))
        if category.startswith('Z'):
            raise Invalid(
                _('Tag "%s" may not contain separator charater U+%04x')
                % (value, ord(ch)))

    return value


def canada_validate_generate_uuid(value: Any):
    """
    Accept UUID-shaped values or generate a uuid for this
    dataset early so that it may be copied into the name field.
    """
    if not value or value is missing:
        return str(uuid.uuid4())
    try:
        return str(uuid.UUID(value))
    except ValueError:
        raise Invalid(_("Badly formed hexadecimal UUID string"))


# pattern from https://html.spec.whatwg.org/#e-mail-state-(type=email)
email_pattern = re.compile(r"^[a-zA-Z0-9.!#$%&'*+\/=?^_`{|}~-]+@[a-zA-Z0-9]"
                           r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9]"
                           r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$")


def email_validator(value: Any):
    if value:
        try:
            if not email_pattern.match(value):
                raise Invalid(_('Please enter a valid email address.'))
        except TypeError:
            raise Invalid(_('Please enter a valid email address.'))
    return value


def geojson_validator(value: Any):
    if value:
        try:
            # accept decoded geojson too
            if isinstance(value, str):
                value = json.loads(value)
            shape = geojson.GeoJSON.to_instance(value, strict=True)
            if not shape.is_valid:
                raise ValueError
            wkt.dumps(shape)
        except Exception:
            raise Invalid(_("Invalid GeoJSON"))
        # must store as JSON
        return json.dumps(value)
    return value


def canada_copy_from_org_name(key: FlattenKey,
                              data: FlattenDataDict,
                              errors: FlattenErrorDict,
                              context: Context):
    """
    When org name at publication not provided, copy from owner_org
    """
    value = data[key]
    if json.loads(value) not in ({}, {'en': '', 'fr': ''}):
        return
    org_id = data[('owner_org',)]
    if not org_id:
        return
    try:
        org = get_action('organization_show')(cast(Context, dict(context)),
                                              {'id': org_id})
    except ObjectNotFound:
        return

    data[key] = json.dumps({
        'en': org['title'].split(' | ')[0],
        'fr': org['title'].split(' | ')[-1],
    })


def canada_maintainer_email_default(key: FlattenKey,
                                    data: FlattenDataDict,
                                    errors: FlattenErrorDict,
                                    context: Context):
    """
    Set to ckanext.canada.default_open_email_address
    if not given and no contact form given.

    This is an output validator.
    """
    em = data[key]
    cf = data.get(('maintainer_contact_form',), '')
    if (not em or em is missing) and (not cf or cf is missing or cf == '{}'):
        data[key] = config['ckanext.canada.default_open_email_address']


def canada_sort_prop_status(key: FlattenKey,
                            data: FlattenDataDict,
                            errors: FlattenErrorDict,
                            context: Context):
    """
    sort the status composite values by date in ascending order
    """
    # this is complicated because data is flattened
    original = []
    n = 0
    while True:
        if ('status', n, 'date') not in data:
            break
        original.append((
            data['status', n, 'date'],
            # some extra fields to sort by to have stable sorting
            data['status', n, 'reason'],
            data['status', n, 'comments'],
            n
        ))
        n += 1
    newmap = {orig[3]: i for i, orig in enumerate(sorted(original))}
    move = {}
    for f in data:
        if f[0] == 'status' and newmap[f[1]] != f[1]:
            move[f] = data[f]
    for f in move:
        data[('status', newmap[f[1]]) + f[2:]] = move[f]


def no_future_date(key: FlattenKey,
                   data: FlattenDataDict,
                   errors: FlattenErrorDict,
                   context: Context):
    ready = data.get(('ready_to_publish',))
    if not ready or ready == 'false':
        return
    value = data.get(key)
    if value and value > datetime.today():
        raise Invalid(_("Date may not be in the future when "
                        "this record is marked ready to publish"))
    return value


def canada_org_title_translated_save(key: FlattenKey,
                                     data: FlattenDataDict,
                                     errors: FlattenErrorDict,
                                     context: Context):
    """Saves a piped string into the core title field.
    E.g. "<English Title> | <French Title>"

    Although fluent now supports organizations, a fair amount of
    core features still do not query title translated fields for groups.

    Required by:
        - Organization Index Search
        - Recombinant CSV Output
        - TODO: add any more required-bys
    """
    try:
        title_translated = fluent_text_output(data[key])
        data[('title',)] = title_translated['en'] + ' | ' + title_translated['fr']
    except KeyError:
        raise StopOnError


def canada_org_title_translated_output(key: FlattenKey,
                                       data: FlattenDataDict,
                                       errors: FlattenErrorDict,
                                       context: Context):
    """
    Return a value for the title field in organization
    schema using a multilingual dict in the form EN | FR.
    """
    data[key] = fluent_text_output(data[key])

    k = key[-1]
    new_key = key[:-1] + (k[:-len(LANG_SUFFIX)],)

    if new_key in data:
        data[new_key] = data[key]['en'] + ' | ' + data[key]['fr']


def protect_reporting_requirements(key: FlattenKey,
                                   data: FlattenDataDict,
                                   errors: FlattenErrorDict,
                                   context: Context):
    """
    Ensure the reporting_requirements field is not
    changed by an unauthorized user.
    """
    if is_sysadmin(context['user']):
        return

    original = ''
    org = context.get('group')
    if org:
        original = org.extras.get('reporting_requirements', [])
    value = data.get(key, [])

    if not value:
        data[key] = original
        return
    elif value == original:
        return
    else:
        errors[key].append("Cannot change value of reporting_requirements field"
                           " from '%s' to '%s'. This field is read-only." %
                           (original, value))
        raise StopOnError


def ati_email_validate(key: FlattenKey,
                       data: FlattenDataDict,
                       errors: FlattenErrorDict,
                       context: Context):
    """
    If ATI is checked for the reporting_requirements
    field, ati_email field becomes mandatory
    """
    if 'ati' in data[key] and not data[('ati_email',)]:
        errors[('ati_email',)].append(
            "ATI email is required for organizations "
            "with ATI selected as a reporting requirement")
        raise StopOnError


def isodate(value: Any, context: Context):
    if isinstance(value, datetime):
        return value
    if value == '':
        return None
    try:
        date = date_str_to_datetime(value)
    except (TypeError, ValueError):
        raise Invalid(_('Date format incorrect. Expecting YYYY-MM-DD'))
    return date


def string_safe(value: Any, context: Context):
    if isinstance(value, text_type):
        return value
    elif isinstance(value, bytes):
        # bytes only arrive when core ckan or plugins call
        # actions from Python code
        try:
            return value.decode('utf8')
        except UnicodeDecodeError:
            return value.decode('cp1252')
    else:
        raise Invalid(_('Must be a Unicode string value'))


def string_safe_stop(key: FlattenKey,
                     data: FlattenDataDict,
                     errors: FlattenErrorDict,
                     context: Context):
    value = data.get(key)
    if isinstance(value, text_type):
        data[key] = value
        return
    elif isinstance(value, bytes):
        # bytes only arrive when core ckan or plugins call
        # actions from Python code
        try:
            data[key] = value.decode('utf8')
            return
        except UnicodeDecodeError:
            data[key] = value.decode('cp1252')
            return
    else:
        errors[key].append(_('Must be a Unicode string value'))
        raise StopOnError


def json_string(value: Any, context: Context):
    try:
        json.loads(value)
    except ValueError:
        raise Invalid(_('Must be a JSON string'))
    return value


def json_string_has_en_fr_keys(value: Any, context: Context):
    try:
        decodedValue = json.loads(value)
        if "en" not in decodedValue:
            raise Invalid(_('JSON object must contain \"en\" key'))
        if "fr" not in decodedValue:
            raise Invalid(_('JSON object must contain \"fr\" key'))
    except ValueError:
        raise Invalid(_('Must be a JSON string'))
    return value


def canada_output_none(value: Any):
    """
    A custom output validator.

    Awlays returns None
    """
    return None


def canada_security_upload_type(key: FlattenKey,
                                data: FlattenDataDict,
                                errors: FlattenErrorDict,
                                context: Context):
    url = data.get(key[:-1] + ('url',))
    upload = data.get(key[:-1] + ('upload',))
    resource = {
        'url': url,
        'upload': upload,
    }
    try:
        validate_upload_type(resource)
    except ValidationError as e:
        # allow a fully empty Resource
        if not url and not upload:
            return
        # type_ignore_reason: incomplete typing
        error = e.error_dict['File'][0]  # type: ignore
        raise Invalid(_(error))


def canada_security_upload_presence(key: FlattenKey,
                                    data: FlattenDataDict,
                                    errors: FlattenErrorDict,
                                    context: Context):
    url = data.get(key[:-1] + ('url',))
    upload = data.get(key[:-1] + ('upload',))
    resource = {
        'url': url,
        'upload': upload,
    }
    try:
        validate_upload_presence(resource)
    except ValidationError as e:
        # allow a fully empty Resource
        if not url and not upload:
            return
        # type_ignore_reason: incomplete typing
        error = e.error_dict['File'][0]  # type: ignore
        raise Invalid(_(error))


def canada_static_charset_tabledesigner(key: FlattenKey,
                                        data: FlattenDataDict,
                                        errors: FlattenErrorDict,
                                        context: Context):
    """
    Always sets to UTF-8 if TableDesigner
    """
    url_type = data.get(key[:-1] + ('url_type',))
    if url_type == 'tabledesigner':
        data[key] = 'UTF-8'


def canada_static_rtype_tabledesigner(key: FlattenKey,
                                      data: FlattenDataDict,
                                      errors: FlattenErrorDict,
                                      context: Context):
    """
    Always sets to dataset if TableDesigner
    """
    url_type = data.get(key[:-1] + ('url_type',))
    if url_type == 'tabledesigner':
        data[key] = 'dataset'


def canada_guess_resource_format(key: FlattenKey,
                                 data: FlattenDataDict,
                                 errors: FlattenErrorDict,
                                 context: Context):
    """
    Guesses the resource format based on the url if missing.
    Guesses the resource format based on url change.
    Always sets to CSV if TableDesigner
    """
    url_type = data.get(key[:-1] + ('url_type',))
    if url_type == 'tabledesigner':
        data[key] = 'CSV'
        return

    value = data[key]

    # if it is empty, then do the initial guess.
    # we will guess all url types, unlike Core
    # which only checks uploaded files.
    if not value or value is missing:
        url = data.get(key[:-1] + ('url',), '')
        if not url:
            return
        try:
            mimetype = get_action('canada_guess_mimetype')(
                context, {"url": url})
            data[key] = mimetype
        except ValidationError:
            # could not guess the format, use `unknown` for now
            data[key] = 'unknown'
            pass
            # TODO: write script/test to loop file extensions
            #      and check if we can guess them. We need to always
            #      set this to something...
            # errors[key].append(e.error_dict['format'])
            # raise StopOnError

    # if there is a resource id, then it is an update.
    # we can check if the url field value has changed.
    resource_id = data.get(key[:-1] + ('id',))
    if resource_id:
        # get the old/current resource url
        current_resource = model.Resource.get(resource_id)
        current_url = None
        if current_resource:
            current_url = current_resource.url
        new_url = data.get(key[:-1] + ('url',), '')
        if not new_url:
            return
        # ckan core will dictize save Resource urls with `rsplit`
        if current_url != new_url and current_url != new_url.rsplit('/', 1)[-1]:
            try:
                mimetype = get_action('canada_guess_mimetype')(
                    context, {"url": new_url})
                data[key] = mimetype
            except ValidationError:
                # could not guess the format, use `unknown` for now
                data[key] = 'unknown'
                pass
                # TODO: write script/test to loop file extensions
                #      and check if we can guess them. We need to always
                #      set this to something...
                # errors[key].append(e.error_dict['format'])
                # raise StopOnError


def protect_registry_access(key: FlattenKey,
                            data: FlattenDataDict,
                            errors: FlattenErrorDict,
                            context: Context):
    """
    Ensure the registry_access field is not changed by an unauthorized user.
    """
    if is_sysadmin(context['user']):
        return

    original = ''
    org_id = data.get(key[:-1] + ('id',))
    org = None
    if org_id:
        org = model.Group.get(org_id)
    if org:
        original = org.extras.get('registry_access', [])

    value = data.get(key, [])

    if not value:
        data[key] = original
        return
    elif value == original:
        return
    else:
        errors[key].append(_("Cannot change value of registry_access field"
                             " from '%s' to '%s'. This field is read-only." %
                             (original, value)))
        raise StopOnError


def limit_resources_per_dataset(key: FlattenKey,
                                data: FlattenDataDict,
                                errors: FlattenErrorDict,
                                context: Context):
    """
    Limits the number of resources per dataset.
    """
    package_id = data.get(key[:-1] + ('id',))

    max_resource_count = config.get(
        'ckanext.canada.max_resources_per_dataset', None)
    if not max_resource_count:
        return

    new_resource_count = len(set(k[1] for k in data.keys() if k[0] == 'resources'))
    if not new_resource_count:
        return

    if new_resource_count > int(max_resource_count):

        # check if a new resource is being added or not, as we need to allow
        # for metadata updates still.
        current_resource_count = model.Session.query(model.Resource.id)\
            .filter(model.Resource.package_id == package_id)\
            .filter(model.Resource.state == 'active').count()
        if not current_resource_count:
            return

        if new_resource_count == current_resource_count:
            # no resources are being added, allow for metadata updates
            return

        errors[('resource_count',)] = [
            _('You can only add up to {max_resource_count} resources to a dataset. '
              'You can segment your resources across multiple datasets or merge your '
              'data to limit the number of resources. Please contact '
              '{support} if you need further assistance.').format(
                  max_resource_count=max_resource_count,
                  support=config.get('ckanext.canada.support_email_address'))]
        raise StopOnError
