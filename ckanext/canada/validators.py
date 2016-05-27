# -*- coding: utf-8 -*-

import unicodedata

from pylons.i18n import _
from ckan.plugins.toolkit import get_validator, Invalid, missing
from ckan.lib.navl.validators import StopOnError
from ckan.new_authz import is_sysadmin
from ckan import model

from ckanext.canada.helpers import may_publish_datasets
from shapely.geometry import asShape
from shapely import wkt
import json
import uuid

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

    caution = re.sub(ur'[\w ]*', u'', value, flags=re.UNICODE)
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


def if_empty_generate_uuid(value):
    """
    Generate a uuid for this dataset early so that it may be
    copied into the name field.
    """
    if not value or value is missing:
        return str(uuid.uuid4())
    return value


def geojson_validator(value):
    if value:
        try:
            # accept decoded geojson too
            if isinstance(value, basestring):
                value = json.loads(value)
            shape = asShape(value)
            wkt.dumps(shape)
        except:
            raise Invalid(_("Invalid GeoJSON"))
        # must store as JSON
        return json.dumps(value)
    return value
