# -*- coding: utf-8 -*-

import re
import unicodedata

from six import text_type

from ckan.plugins.toolkit import _, h, get_action, ValidationError
from ckan.lib.navl.validators import StopOnError
from ckan.authz import is_sysadmin
from ckan import model

from ckanext.canada.helpers import may_publish_datasets
import geojson
from geomet import wkt
import json
import uuid
from datetime import datetime

from ckanapi import LocalCKAN, NotFound
from ckan.lib.helpers import date_str_to_datetime
from ckantoolkit import get_validator, Invalid, missing
from ckanext.fluent.validators import fluent_text_output, LANG_SUFFIX
from ckan.logic import ValidationError
from ckanext.security.resource_upload_validator import (
    validate_upload_type, validate_upload_presence
)

not_empty = get_validator('not_empty')
ignore_missing = get_validator('ignore_missing')

MIN_TAG_LENGTH = 2
MAX_TAG_LENGTH = 140  # because twitter


def protect_portal_release_date(key, data, errors, context):
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


def user_read_only(key, data, errors, context):
    # sysadmins are free to change fields as they like
    if is_sysadmin(context['user']) and data[key] is not missing:
        return

    assert len(key) == 1, 'only package fields supported user_read_only (not %r)' % key

    original = ''
    package = context.get('package')
    if not package and data[key] is not missing:
        errors[key].append("Only sysadmin may set this value")
        raise StopOnError

    if hasattr(package, key[0]):
        data[key] = getattr(package, key[0])
    elif package:
        data[key] = package.extras.get(key[0], '')


def user_read_only_json(key, data, errors, context):
    # sysadmins are free to change fields as they like
    if is_sysadmin(context['user']) and data[key] is not missing:
        return

    assert len(key) == 1, 'only package fields supported user_read_only (not %r)' % key

    original = ''
    package = context.get('package')
    if not package and data[key] is not missing:
        errors[key].append("Only sysadmin may set this value")
        raise StopOnError

    if hasattr(package, key[0]):
        data[key] = json.loads(getattr(package, key[0]))
    else:
        data[key] = json.loads(package.extras.get(key[0], 'None'))


def canada_tags(value, context):
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
            _(u'Tag "%s" length is less than minimum %s')
            % (value, MIN_TAG_LENGTH))
    if len(value) > MAX_TAG_LENGTH:
        raise Invalid(
            _(u'Tag "%s" length is more than maximum %i')
            % (value, MAX_TAG_LENGTH))
    if u'  ' in value:
        raise Invalid(
            _(u'Tag "%s" may not contain consecutive spaces') % (value,))

    caution = re.sub(ur'[\w ]*', u'', value)
    for ch in caution:
        category = unicodedata.category(ch)
        if category.startswith('C'):
            raise Invalid(
                _(u'Tag "%s" may not contain unprintable character U+%04x')
                % (value, ord(ch)))
        if category.startswith('Z'):
            raise Invalid(
                _(u'Tag "%s" may not contain separator charater U+%04x')
                % (value, ord(ch)))

    return value


def canada_validate_generate_uuid(value):
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

#pattern from https://html.spec.whatwg.org/#e-mail-state-(type=email)
email_pattern = re.compile(r"^[a-zA-Z0-9.!#$%&'*+\/=?^_`{|}~-]+@[a-zA-Z0-9]"\
                           "(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9]"\
                           "(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$")


def email_validator(value):
    if value:
        try:
            if not email_pattern.match(value):
                raise Invalid(_('Please enter a valid email address.'))
        except TypeError:
            raise Invalid(_('Please enter a valid email address.'))
    return value


def geojson_validator(value):
    if value:
        try:
            # accept decoded geojson too
            if isinstance(value, basestring):
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

def canada_copy_from_org_name(key, data, errors, context):
    """
    When org name at publication not provided, copy from owner_org
    """
    value = data[key]
    if json.loads(value) not in ({}, {'en':'', 'fr':''}):
        return
    org_id = data[('owner_org',)]
    if not org_id:
        return
    try:
        org = LocalCKAN(username='').action.organization_show(id=org_id)
    except NotFound:
        return

    data[key] = json.dumps({
        'en': org['title'].split(' | ')[0],
        'fr': org['title'].split(' | ')[-1],
    })

def canada_non_related_required(key, data, errors, context):
    """
    Required resource field *if* this resource is not a related item
    """
    if not data.get(key[:-1] + ('related_type',)):
        return not_empty(key, data, errors, context)
    return ignore_missing(key, data, errors, context)


def canada_maintainer_email_default(key, data, errors, context):
    """
    Set to open-ouvert@tbs-sct.gc.ca if not given and no contact form given
    """
    em = data[key]
    cf = data.get(('maintainer_contact_form',), '')
    if (not em or em is missing) and (not cf or cf is missing or cf == '{}'):
        data[key] = 'open-ouvert@tbs-sct.gc.ca'


def canada_sort_prop_status(key, data, errors, context):
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


def no_future_date(key, data, errors, context):
    ready = data.get(('ready_to_publish',))
    if not ready or ready == 'false':
        return
    value = data.get(key)
    if value and value > datetime.today():
        raise Invalid(_("Date may not be in the future when this record is marked ready to publish"))
    return value


def canada_org_title_translated_save(key, data, errors, context):
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


def canada_org_title_translated_output(key, data, errors, context):
    """
    Return a value for the title field in organization schema using a multilingual dict in the form EN | FR.
    """
    data[key] = fluent_text_output(data[key])

    k = key[-1]
    new_key = key[:-1] + (k[:-len(LANG_SUFFIX)],)

    if new_key in data:
        data[new_key] = data[key]['en'] + ' | ' + data[key]['fr']


def protect_reporting_requirements(key, data, errors, context):
    """
    Ensure the reporting_requirements field is not changed by an unauthorized user.
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


def ati_email_validate(key, data, errors, context):
    """
    If ATI is checked for the reporting_requirements field, ati_email field becomes mandatory
    """
    if 'ati' in data[key] and not data[('ati_email',)]:
        errors[('ati_email',)].append("ATI email is required for organizations with ATI selected as a reporting requirement")
        raise StopOnError

def isodate(value, context):
    if isinstance(value, datetime):
        return value
    if value == '':
        return None
    try:
        date = date_str_to_datetime(value)
    except (TypeError, ValueError) as e:
        raise Invalid(_('Date format incorrect. Expecting YYYY-MM-DD'))
    return date

def string_safe(value, context):
    if isinstance(value, text_type):
        return value
    elif isinstance(value, bytes):
        # bytes only arrive when core ckan or plugins call
        # actions from Python code
        try:
            return value.decode(u'utf8')
        except UnicodeDecodeError:
            return value.decode(u'cp1252')
    else:
        raise Invalid(_('Must be a Unicode string value'))

def string_safe_stop(key, data, errors, context):
    value = data.get(key)
    if isinstance(value, text_type):
        return value
    elif isinstance(value, bytes):
        # bytes only arrive when core ckan or plugins call
        # actions from Python code
        try:
            return value.decode(u'utf8')
        except UnicodeDecodeError:
            return value.decode(u'cp1252')
    else:
        errors[key].append(_('Must be a Unicode string value'))
        raise StopOnError

def json_string(value, context):
    try:
        json.loads(value)
    except ValueError:
        raise Invalid(_('Must be a JSON string'))
    return value

def json_string_has_en_fr_keys(value, context):
    try:
        decodedValue = json.loads(value)
        if "en" not in decodedValue:
            raise Invalid(_('JSON object must contain \"en\" key'))
        if "fr" not in decodedValue:
            raise Invalid(_('JSON object must contain \"fr\" key'))
    except ValueError:
        raise Invalid(_('Must be a JSON string'))
    return value


def canada_output_none(value):
    """
    A custom output validator.

    Awlays returns None
    """
    return None


def canada_security_upload_type(key, data, errors, context):
    url_type = data.get(key[:-1] + ('url_type',))
    url = data.get(key[:-1] + ('url',))
    upload = data.get(key[:-1] + ('upload',))
    resource = {
        'url': url,
        'upload': upload,
    }
    try:
        validate_upload_type(resource)
    except ValidationError as e:
        if url_type == 'tabledesigner':
            return
        error = e.error_dict['File'][0]
        raise Invalid(_(error))


def canada_security_upload_presence(key, data, errors, context):
    url_type = data.get(key[:-1] + ('url_type',))
    url = data.get(key[:-1] + ('url',))
    upload = data.get(key[:-1] + ('upload',))
    resource = {
        'url': url,
        'upload': upload,
    }
    try:
        validate_upload_presence(resource)
    except ValidationError as e:
        if url_type == 'tabledesigner':
            return
        error = e.error_dict['File'][0]
        raise Invalid(_(error))


def canada_static_charset_tabledesigner(key, data, errors, context):
    """
    Always sets to UTF-8 if TableDesigner
    """
    url_type = data.get(key[:-1] + ('url_type',))
    if url_type == 'tabledesigner':
        data[key] = 'UTF-8'


def canada_static_rtype_tabledesigner(key, data, errors, context):
    """
    Always sets to dataset if TableDesigner
    """
    url_type = data.get(key[:-1] + ('url_type',))
    if url_type == 'tabledesigner':
        data[key] = 'dataset'


def canada_guess_resource_format(key, data, errors, context):
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
            mimetype = get_action('canada_guess_mimetype')(context, {"url": url})
            data[key] = mimetype
        except ValidationError as e:
            # could not guess the format, use `unknown` for now
            data[key] = 'unknown'
            pass
            #TODO: write script/test to loop file extensions
            #      and check if we can guess them. We need to always
            #      set this to something...
            #errors[key].append(e.error_dict['format'])
            #raise StopOnError

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
        if current_url != new_url:
            try:
                mimetype = get_action('canada_guess_mimetype')(context, {"url": new_url})
                data[key] = mimetype
            except ValidationError as e:
                # could not guess the format, use `unknown` for now
                data[key] = 'unknown'
                pass
                #TODO: write script/test to loop file extensions
                #      and check if we can guess them. We need to always
                #      set this to something...
                #errors[key].append(e.error_dict['format'])
                #raise StopOnError


def protect_registry_access(key, data, errors, context):
    """
    Ensure the registry_access field is not changed by an unauthorized user.
    """
    if is_sysadmin(context['user']):
        return

    original = ''
    org_id = data.get(key[:-1] + ('id',))
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
