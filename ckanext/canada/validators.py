# -*- coding: utf-8 -*-

import re
import unicodedata

from pylons.i18n import _
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
from ckantoolkit import get_validator, Invalid, missing

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


def canada_tags(value, context):
    """
    Accept
    - unicode graphical (printable) characters
    - single internal spaces (no double-spaces)

    Reject
    - commas
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
    if u',' in value:
        raise Invalid(_(u'Tag "%s" may not contain commas') % (value,))
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


def if_empty_set_to(default_value):
    """
    Provide a default value when not given by user
    """
    def validator(value):
        if not value or value is missing:
            return default_value
        return value

    return validator


def no_future_date(value):
    if value > datetime.today():
        raise Invalid(_("Date may not be in the future"))
    return value
