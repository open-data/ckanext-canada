from typing import Optional, Type, Any, List

from frictionless import Check, Plugin as FrictionlessPlugin

from ckan.plugins.toolkit import config, asbool
from ckanext.canada import checks


class CanadaValidationPlugin(FrictionlessPlugin):
    def select_check_class(self, type: Optional[str] = None) -> Optional[Type[Check]]:
        """
        Load custom check classes.
        """
        if type == 'ds-headers':
            return checks.DatastoreHeadersCheck()

    def detect_field_candidates(self, field_candidates: List[dict[str, Any]]):
        """
        Set list of available types for Resource table fields.
        """
        if asbool(config.get('ckanext.validation.use_type_guessing', False)):
            return
        field_candidates.clear()
        field_candidates.append({'type': 'string'})
