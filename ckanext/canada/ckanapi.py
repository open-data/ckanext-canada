"""
ckanapi
-------

This module a thin wrapper around the CKAN's action API.

It may be used from within a plugin or if only using RemoteCKAN
it may be used separate from CKAN.
"""

import urllib2
import json

class CKANAPIError(Exception):
    """
    The error raised from RemoteCKAN.call_action when no other error
    is recognized.

    If importing CKAN source fails then new versions of ParameterError,
    NotAuthorized, ValidationError, NotFound, ParameterError,
    SearchQueryError and SearchError are created as subclasses of this
    class so that they provide a helpful str() for tracebacks.
    """
    def __str__(self):
        return repr(self.args)

try:
    from ckan.logic import (ParameterError, NotAuthorized, NotFound,
                            ValidationError)
    from ckan.lib.search import SearchQueryError, SearchError

except ImportError:
    # Implement the minimum to be compatible with existing errors
    # without requiring CKAN

    class NotAuthorized(CKANAPIError):
        pass

    class ValidationError(CKANAPIError):
        def __init__(self, error_dict):
            self.error_dict = error_dict
        def __str__(self):
            return repr(self.error_dict)

    class NotFound(CKANAPIError):
        def __init__(self, extra_msg):
            self.extra_msg = extra_msg
        def __str__(self):
            return self.extra_msg

    class ParameterError(CKANAPIError):
        def __init__(self, extra_msg):
            self.extra_msg = extra_msg
        def __str__(self):
            return self.extra_msg

    class SearchQueryError(CKANAPIError):
        pass

    class SearchError(CKANAPIError):
        pass


class ActionShortcut(object):
    """
    ActionShortcut(foo).bar(baz=2) <=> foo.call_action('bar', {'baz':2})

    An instance of this class is used as the .action attribute of
    LocalCKAN and RemoteCKAN instances to provide a short way to call
    actions, e.g::

        demo = RemoteCKAN('http://demo.ckan.org')
        pkg = demo.action.package_show(id='adur_district_spending')

    instead of::

        demo = RemoteCKAN('http://demo.ckan.org')
        pkg = demo.call_action('package_show', {'id':'adur_district_spending'})

    """
    def __init__(self, ckan):
        self._ckan = ckan

    def __getattr__(self, name):
        def action(**kwargs):
            return self._ckan.call_action(name, kwargs)
        return action


class LocalCKAN(object):
    """
    An interface to calling actions with get_action() for CKAN plugins.

    :param username: perform action as this user, defaults to the site user
                     and stored as self.username
    :param context: a default context dict to use when calling actions,
                    stored as self.context with username added as its 'user'
                    value
    """
    def __init__(self, username=None, context=None):
        from ckan.logic import get_action
        self._get_action = get_action

        if not username:
            username = self.get_site_username()
        self.username = username
        self.context = dict(context or [], user=self.username)
        self.action = ActionShortcut(self)

    def get_site_username(self):
        user = self._get_action('get_site_user')({'ignore_auth': True}, ())
        return user['name']

    def call_action(self, action, data_dict=None, context=None):
        """
        :param action: the action name, e.g. 'package_create'
        :param data_dict: the dict to pass to the action, defaults to {}
        :param context: an override for the context to use for this action,
                        remember to include a 'user' when necessary
        """
        if not data_dict:
            data_dict = []
        if context is None:
            context = self.context
        # copy dicts because actions may modify the dicts they are passed
        return self._get_action(action)(dict(context), dict(data_dict))


class RemoteCKAN(object):
    """
    An interface to the the CKAN API actions on a remote CKAN instance.

    :param address: the web address of the CKAN instance, e.g.
                    'http://demo.ckan.org', stored as self.address
    :param api_key: the API key to pass as an 'Authorization' header
                    when actions are called, stored as self.api_key
    """
    def __init__(self, address, api_key=None):
        self.address = address
        self.api_key = api_key
        self.action = ActionShortcut(self)

    def call_action(self, action, data_dict=None):
        """
        :param action: the action name, e.g. 'package_create'
        :param data_dict: the dict to pass to the action as JSON,
                          defaults to {}

        This function parses the response from the server as JSON and
        returns the decoded value.  When an error is returned this
        function will convert it back to an exception that matches the
        one the action function itself raised.
        """
        if not data_dict:
            data_dict = {}
        data = json.dumps(data_dict)
        header = {'Content-Type': 'application/json'}
        if self.api_key:
            header['Authorization'] = self.api_key
        url = self.address + '/api/action/' + action
        req = urllib2.Request(url, data, headers=header)
        try:
            r = urllib2.urlopen(req)
            status = r.getcode()
            response = r.read()
        except urllib2.HTTPError, e:
            status = e.code
            response = e.read()
        return reverse_apicontroller_action(response, status)


def reverse_apicontroller_action(response, status):
    """
    Make an API call look like a direct action call by reversing the
    exception -> HTTP response translation that APIController.action does
    """
    try:
        parsed = json.loads(response)
        if status == 200:
            return parsed
        if hasattr(parsed, 'get'):
            err = parsed.get('error', {})
        else:
            err = {}
    except ValueError:
        err = {}

    etype = err.get('__type')
    emessage = err.get('message', '').split(': ', 1)[-1]
    if etype == 'Search Query Error':
        # I refuse to eval(emessage), even if it would be more correct
        raise SearchQueryError(emessage) 
    elif etype == 'Search Error':
        # I refuse to eval(emessage), even if it would be more correct
        raise SearchError(emessage) 
    elif etype == 'Parameter Error':
        raise ParameterError(emessage)
    elif etype == 'Validation Error':
        raise ValidationError(err)
    elif etype == 'Not Found Error':
        raise NotFound(emessage)
    elif etype == 'Authorization Error':
        raise NotAuthorized()

    # don't recognize the error
    raise CKANAPIError(response, status)
