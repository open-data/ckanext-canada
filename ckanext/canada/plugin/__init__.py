from .dataset_plugin import CanadaDatasetsPlugin
from .form_plugin import CanadaFormsPlugin
from .internal_plugin import CanadaInternalPlugin
from .public_plugin import CanadaPublicPlugin
from .security_plugin import CanadaSecurityPlugin
from .theme_plugin import CanadaThemePlugin
from .validation_plugin import CanadaValidationPlugin

# XXX Monkey patch to work around libcloud/azure 400 error on get_container
try:
    import libcloud.common.azure
    libcloud.common.azure.API_VERSION = '2014-02-14'
except ImportError:
    pass

__all__ = [
    'CanadaDatasetsPlugin',
    'CanadaFormsPlugin',
    'CanadaInternalPlugin',
    'CanadaPublicPlugin',
    'CanadaSecurityPlugin',
    'CanadaThemePlugin',
    'CanadaValidationPlugin'
]
