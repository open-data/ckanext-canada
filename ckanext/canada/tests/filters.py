"""
Filter scripts are not part of the installed ckanext-canada module.
We're assuming a source install and redirecting the import to run tests.
"""
import os
import sys

bin_filter_path = os.path.join(
    os.path.dirname(str(__file__)),
    '../../../bin/filter')

sys.path.append(bin_filter_path)
import filter_service_std  # noqa: E402
import filter_contracts  # noqa: E402
sys.path.pop()

__all__ = ['filter_service_std', 'filter_contracts']

for f in __all__:
    sys.modules.pop(f)
