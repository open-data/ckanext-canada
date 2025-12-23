from .logic_plugin import CanadaLogicPlugin
from .theme_plugin import CanadaThemePlugin

# XXX Monkey patch to work around libcloud/azure 400 error on get_container
try:
    import libcloud.common.azure
    libcloud.common.azure.API_VERSION = '2014-02-14'  # type: ignore
except ImportError:
    pass

__all__ = [
    'CanadaLogicPlugin',
    'CanadaThemePlugin'
]
