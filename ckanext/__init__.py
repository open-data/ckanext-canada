# this is a namespace package
try:
    # type_ignore_reason: try/catch
    import pkg_resources  # type: ignore
    # type_ignore_reason: reportAttributeAccessIssue
    pkg_resources.declare_namespace(__name__)
except ImportError:
    import pkgutil
    __path__ = pkgutil.extend_path(__path__, __name__)
