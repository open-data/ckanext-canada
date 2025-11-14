import random
import string

from typing import Any, Optional, List, Tuple
from ckan.common import CKANConfig

from ckan.plugins.toolkit import g


class CSPNonceMiddleware(object):
    def __init__(self, app: Any, config: 'CKANConfig'):
        self.config = config
        self.app = app

    def __call__(self, environ: Any, start_response: Any) -> Any:
        csp_nonce = ''.join(random.choices(
                string.ascii_letters + string.digits, k=22))
        environ['CSP_NONCE'] = csp_nonce
        csp_header = [
            ('Content-Security-Policy',
             self.config['ckanext.canada.content_security_policy'].replace(
                 '[[NONCE]]', csp_nonce))]

        def _start_response(status: str,
                            response_headers: List[Tuple[str, str]],
                            exc_info: Optional[Any] = None):
            return start_response(
                status,
                response_headers if self.config[
                    'ckanext.canada.disable_content_security_policy']
                else response_headers + csp_header,
                exc_info)

        return self.app(environ, _start_response)


class LogExtraMiddleware(object):
    def __init__(self, app: Any, config: 'CKANConfig'):
        self.app = app

    def __call__(self, environ: Any, start_response: Any) -> Any:
        def _start_response(status: str,
                            response_headers: List[Tuple[str, str]],
                            exc_info: Optional[Any] = None):
            extra = []
            try:
                contextual_user = g.user
            except (TypeError, RuntimeError, AttributeError):
                contextual_user = None
            if contextual_user:
                log_extra = g.log_extra if hasattr(g, 'log_extra') else ''
                # FIXME: make sure username special chars are handled
                # the values in the tuple HAVE to be str types.
                extra = [('X-LogExtra', f'user={contextual_user} {log_extra}')]

            return start_response(
                status,
                response_headers + extra,
                exc_info)

        return self.app(environ, _start_response)
